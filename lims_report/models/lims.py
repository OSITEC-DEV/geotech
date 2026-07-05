# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import itertools

from odoo import api, fields, models, _
from odoo.exceptions import UserError



class Lims(models.Model):
    _inherit = 'lims.sample.main'

    report_ids = fields.One2many('lims.report', 'main_id', 'Reports', copy=False)
    report_count = fields.Integer('Number of reports', compute='_get_reports')
    group_by_report = fields.Selection(
        [('package', 'BY Pack'), ('print_group', 'BY Print Group'), ('sample', 'BY Sample')],
        default='print_group')
    external_accession_number = fields.Text("", help="Useful for report searching in portal")
    report_only_index = fields.Boolean("Report only Index analysis", default=True,
                                       help="Avoid creating the family members analysis in a separate report")

    @api.depends('report_ids')
    def _get_reports(self):
        for order in self:
            reports = order.report_ids.filtered(lambda r: r.state != 'cancel')
            order.report_count = len(reports)
            return len(reports)

    def action_view_reports(self):
        report_ids = self.mapped('report_ids')
        action = self.env["ir.actions.actions"]._for_xml_id("lims_report.reports_action")
        if len(report_ids) > 1:
            action['domain'] = [('id', 'in', report_ids.ids)]
        elif len(report_ids) == 1:
            form_view = [(self.env.ref('lims_report.lims_view_form_report').id, 'form')]
            if 'views' in action:
                action['views'] = form_view + [(state, view) for state, view in action['views'] if view != 'form']
            else:
                action['views'] = form_view
            action['res_id'] = report_ids.id
        else:
            action = {'type': 'ir.actions.act_window_close'}

        context = {
            'default_company_id': self.env.company.id,
        }
        if len(self) == 1:
            context.update({
                'default_partner_id': self.partner_id.id,
                'default_main_id': self.id,
                'default_user_id': self.user_id.id,
            })
        action['context'] = context
        return action

    def _prepare_report_values(self, product, default_values):
        return {
            'name': self.name,
            'main_id': self.id,
            'product_id': product.id if product else False,
            'date': fields.Datetime.now(),
            'hide_table_result': default_values.get('default_hide_table', False),
            'notes': default_values.get('notes', False),
            'print_note': default_values.get('print_note', False),
            'user_id': self.env.user.id,
        }

    def create_report(self):
        for record in self:
            if record.state not in ['progress', 'tosend', 'done']:
                continue

            partner_id_list = [record.partner_id.id] + [p.id for p in record.partner_ids]
            # Deduplicate while preserving order
            seen = set()
            partner_id_list = [p for p in partner_id_list if p and not (p in seen or seen.add(p))]
            if not partner_id_list and record.partner_id:
                partner_id_list = [record.partner_id.id]
            message_error = ()
            res = False
            individual_test = False
            main_partner_id = record.partner_id.id
            for partner_id in partner_id_list:
                is_main = (partner_id == main_partner_id)
                analyses = record.analysis_ids.filtered(
                    lambda a, p=partner_id, m=is_main: (
                        a.partner_id.id == p or (m and not a.partner_id)
                    ) and (
                        (a.state == 'valid' and not a.report_id) or
                        (a.report_id and a.report_id.state == 'cancel')
                    )
                )

                if not analyses:
                    message_error += (f"No analysis found to report for Customer ID {partner_id}\n",)
                    continue

                # Group analyses by sample_line_id
                sample_groups = {}
                for a in analyses:
                    key = a.sample_line_id
                    sample_groups.setdefault(key, []).append(a)

                for sample, sample_analyses in sample_groups.items():

                    if record.group_by_report == 'print_group':
                        # One report per lims.sample.preparation — template groups by print_group_id
                        default_values = {}
                        auto_validate_report = False
                        for a in sample_analyses:
                            dept = a.department_id
                            if dept and dept.default_hide_table:
                                default_values['default_hide_table'] = True
                            if dept and dept.text_in_report:
                                default_values['notes'] = dept.text_in_report
                            if dept and dept.subcontracting_note:
                                default_values['print_note'] = True
                            if dept and dept.auto_validate_report:
                                auto_validate_report = True

                        values = record._prepare_report_values(False, default_values)
                        values.update({
                            'analysis_ids': [(6, 0, [a.id for a in sample_analyses])],
                            'partner_id': partner_id,
                            'name': f"{record.name}-{sample.name if sample else ''}",
                            'title': (sample.sample_name or sample.name) if sample else record.name,
                        })
                        report = record.env['lims.report'].create(values)
                        if auto_validate_report:
                            report.do_validate()
                        followers = record._refresh_followers()
                        report.message_subscribe(followers)
                        res = True

                    else:
                        analysis_pack = []
                        sample_group = []

                        for a in sample_analyses:
                            if a.pack_selected and record.group_by_report == 'package':
                                analysis_pack.append((a, a.pack_selected))
                            elif record.group_by_report == 'sample':
                                if not a.sample_line_id:
                                    continue
                                sample_group.append((a, a.sample_line_id))
                            else:
                                # Individual test (fallback)
                                individual_test = record.env['lims.report'].create({
                                    'name': f"{record.name}-Sample{sample.id if sample else ''}",
                                    'main_id': record.id,
                                    'product_id': a.product_id.id if a.product_id else False,
                                    'date': fields.Datetime.now(),
                                    'user_id': record.env.user.id,
                                    'analysis_ids': [(4, a.id)],
                                    'partner_id': partner_id,
                                })
                                res = True

                        if analysis_pack and record.group_by_report == 'package':
                            record._create_report(analysis_pack, partner_id)
                            res = True

                        if sample_group and record.group_by_report == 'sample':
                            record._create_report(sample_group, partner_id)
                            res = True

            # Post messages
            if res or individual_test:
                if message_error:
                    record.message_post(body="\n".join(message_error))
                return {
                    'effect': {
                        'fadeout': 'slow',
                        'message': 'Report has been created',
                        'type': 'rainbow_man',
                    }
                }
            else:
                record.message_post(body="Report not created for analysis")

    def _create_report(self, lista, patient):
        analysis_ids = []
        product = False
        lista = sorted(lista, key=lambda x: x[1])  # sort by group key
        i = 0

        for k, lines in itertools.groupby(lista, key=lambda x: x[1]):
            default_values = {}
            auto_validate_report = False
            analysis_ids.clear()

            for item in lines:
                a = item[0]
                analysis_ids.append(a.id)
                department = a.department_id
                if department.default_hide_table:
                    default_values['default_hide_table'] = True
                if department.text_in_report:
                    default_values['notes'] = department.text_in_report
                if department.subcontracting_note:
                    default_values['print_note'] = True
                if department.auto_validate_report:
                    auto_validate_report = True

            if k._name == 'product.product':
                product = k.product_variant_id

            i += 1
            values = self._prepare_report_values(product, default_values)
            values.update({
                'print_group_id': k.id if k._name == 'lims.parameter.print.group' else False,
                'analysis_ids': [(6, 0, analysis_ids)],
                'partner_id': patient,
                'name': f"{self.name}-{i}",
                'title': product.name if product else k.name
            })

            report = self.env['lims.report'].create(values)

            if auto_validate_report:
                report.do_validate()

            followers = self._refresh_followers()
            report.message_subscribe(followers)

    def _refresh_followers(self):
        followers = []
        followers.append(self.partner_id.id) if self.partner_id.id not in self.message_follower_ids.ids else False
        return followers

    def do_reject(self):
        res = super(Lims, self).do_reject()
        if not any(self.report_ids.filtered(lambda r: r.state in ['valid', 'sent'])):
            return res
        else:
            raise UserError("The report of this request already has been validated")

