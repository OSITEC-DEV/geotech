# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import base64
import itertools
import json
import logging
from datetime import datetime, timedelta
from io import BytesIO
import numpy as np
import qrcode
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


def _next_lab_seq(env, code, lab_id, seq_date=None):
    """Return the next sequence value for *code* that belongs to *lab_id*.
    Falls back to any sequence with that code when no lab-specific one exists.

    seq_date may be a timezone-aware datetime (from context_timestamp); we
    strip tzinfo before passing it to ir.sequence._next() because the ORM
    rejects tz-aware values when they propagate into Datetime field writes
    inside the date-range sequence machinery.
    """
    if seq_date and getattr(seq_date, 'tzinfo', None):
        seq_date = seq_date.replace(tzinfo=None)
    seq = env['ir.sequence'].search(
        [('code', '=', code), ('laboratory_id', '=', lab_id)], limit=1
    )
    if seq:
        return seq.with_context(ir_sequence_date=seq_date)._next()
    return env['ir.sequence'].next_by_code(code, sequence_date=seq_date) or _('New')


class Lims_sample(models.Model):
    _name = 'lims.sample.main'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'sequence.mixin', 'utm.mixin']
    _description = 'Analysis Request'
    _order = 'date desc, planned_date desc'

    @api.depends('sample_line')
    def get_all_patients_of_request(self):
        for record in self:
            if len(record.sample_line):
                patient_list = []
                for line in record.sample_line:
                    if line.partner_id:
                        patient_list.append((4, line.partner_id.id))
                record.partner_ids = patient_list
            else:
                continue
            return patient_list

    def _get_default_template(self):
        return self.env.company.translation_template.id

    sale_id = fields.Many2one('sale.order', string='Quotation', help='Clic generate quotation button', tracking=True,
                              copy=False)
    name = fields.Char('Number', copy=False, index=True, default='New', readonly=True)
    user_id = fields.Many2one('res.users', 'Responsible', default=lambda self: self.env.user, tracking=True)
    origin = fields.Char('Origin', default="On-site")
    tags = fields.Many2many('crm.tag')
    date = fields.Datetime('Registration Date', default=lambda self: fields.datetime.now(), tracking=True)
    planned_date = fields.Datetime('Planned date', copy=False)
    receiving_date = fields.Datetime('Receiving date', copy=False)
    partner_id = fields.Many2one('res.partner', 'Customer', tracking=True, index=True)
    sample_line = fields.One2many('lims.sample.line', 'main_id', 'Requests', copy=True)
    notes = fields.Text('Notes')
    state = fields.Selection(
        [('draft', 'Draft'), ('confirm', 'Confirmed'), ('recieved', 'Received'), ('progress', 'In progress'),
         ('tosend', 'To Send'), ('done', 'Done'), ('reject', 'Rejected')], default='draft', tracking=True)
    company_id = fields.Many2one('res.company', 'company', default=lambda self: self.env.company.id)
    sample_line_prepared = fields.One2many('lims.sample.preparation', 'main_id', 'Samples')
    analysis_ids = fields.One2many('lims.analysis', 'main_id', 'Analysis', copy=False)
    analysis_count = fields.Integer(string='Tests Count', compute='_get_analysis')
    analysis_done = fields.Boolean(string='Completed Tests', compute='_compute_analysis_done')
    report_date = fields.Datetime('Report date', tracking=True)
    qrcode = fields.Binary('QRcode', attachment=True, store=True)
    # excel_file = fields.Binary(string='Download Report Excel',readonly="1")
    # file_name = fields.Char(string='Excel File',readonly="1")
    invoicing_type = fields.Selection(
        [('foc', 'FreeOfCharge'), ('pt', 'Proficiency Testing'), ('quot', 'Sale Order'), ('invoice', 'Invoice')],
        default='quot')
    invoice_ids = fields.One2many('account.move', 'main_id', string='Invoices')
    amount_total = fields.Float('Amount Total', compute='_amount_total')
    translation_template = fields.Many2one('lims.translate.titles', default=_get_default_template)
    diff_time = fields.Float(" Delta(hours)", compute='_compute_diff_time')
    delay_time = fields.Float("Delay", copy=False)
    signature_consult = fields.Binary("Consultant Signature", copy=False)
    signature_quality = fields.Binary("QA Signature", copy=False)
    signature_director = fields.Binary("Director Signature", copy=False)
    source = fields.Selection([('standard', 'Standard Customer'), ('contract', 'Contract Customer')]
                              , default='standard', string="Customer source", tracking=True)
    reason_id = fields.Many2one('lims.reason.type', 'Reason', tracking=True, readonly=True)
    date_done = fields.Datetime('Date done')
    tat = fields.Float('TAT')
    priority = fields.Selection([('low', 'Low'), ('normal', 'Normal'), ('high', 'High'), ('urgent', 'Urgent')],
                                default="normal")
    print_method = fields.Boolean("Print Method")

    partner_ids = fields.Many2many('res.partner', string='All customer', relation='request_patient_rel',
                                   compute='get_all_patients_of_request', store=True)
    tracking_number = fields.Char("Tracking N")
    logistic_company = fields.Selection([('DHL', 'DHL'), ('UPS', 'UPS'), ('ARAMEX', 'ARAMEX'), ('AJEX', 'AJEX')])
    active = fields.Boolean('Active', default=True)
    has_samples_to_receive = fields.Boolean(string="Has Samples to Receive", compute="_compute_has_samples_to_receive",
                                            store=True)
    laboratory_id = fields.Many2one("lims.laboratory", "Laboratory", required=True,
                                    default=lambda self: self.env.user.default_laboratory_id.id, tracking=True)
    approved_foc = fields.Boolean("Approved FOC", tracking=True, help="Check to approve Free Of Charge request")
    salesperson = fields.Many2one("res.partner", "SalesPerson", compute='get_salesperson', store=True, readonly=False)
    lock = fields.Boolean(string='Lock', default=False,
                          help='Lock request so that further'
                               ' modifications are not possible.')
    unlock_datetime = fields.Datetime("Unlock Datetime", tracking=True)
    unlock_reason = fields.Char("Unlock reason", tracking=True)

    def _cron_auto_lock_samples(self):
        now = fields.Datetime.now()

        records = self.search([
            ('lock', '=', False),
            ('unlock_datetime', '!=', False),
            ('unlock_datetime', '<=', now),
        ])

        for rec in records:
            rec.lock = True
            rec.mapped('sample_line').write({'lock': True})
            rec.mapped('sample_line_prepared').write({'lock': True})

    def action_lock(self):
        """ Lock Request """
        self.lock = True
        for rec in self:
            rec.lock = True
            rec.mapped('sample_line').write({'lock': True})
            rec.mapped('sample_line_prepared').write({'lock': True})

    def action_to_unlock(self):
        """Open unlock wizard"""
        self.ensure_one()

        return {
            "type": "ir.actions.act_window",
            "name": "Unlock Sample",
            "res_model": "lims.sample.unlock.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_request_ids": self.ids
            }
        }

    @api.depends('sale_id')
    def get_salesperson(self):
        for record in self:
            if record.sale_id:
                sales_user = record.sale_id.user_id
                record.salesperson = sales_user.partner_id.id

    @api.depends('sample_line_prepared.state')
    def _compute_has_samples_to_receive(self):
        for record in self:
            record.has_samples_to_receive = bool(record.sample_line_prepared) and any(
                s.state == 'todo' for s in record.sample_line_prepared
            )

    def action_accept_all(self):
        samples = self.filtered(lambda s: s.state != 'recieved')
        samples.do_recieve()

    @api.depends('planned_date', 'report_date')
    def _compute_diff_time(self):
        # time_reciept = self.date.strftime("%m/%d/%Y, %H:%M")
        # time_send = self.report_date.strftime("%m/%d/%Y, %H:%M")
        for record in self:
            if record.planned_date:
                if not record.report_date:
                    current_time = (fields.datetime.now() - record.planned_date)
                    minutes = divmod(current_time.total_seconds(), 60)[0] / 60
                    record.diff_time = minutes
                    return current_time
                else:
                    current_time = (record.report_date - record.planned_date)
                    minutes = divmod(current_time.total_seconds(), 60)[0] / 60
                    record.diff_time = minutes if minutes else 0.0
            else:
                record.diff_time = 0.0

    def _amount_total(self):
        invoice_ids = self.invoice_ids.filtered(lambda inv: inv.state == 'posted')
        res = sum(inv.amount_total for inv in invoice_ids) if invoice_ids else 0.0
        self.amount_total = res
        return res

    def send_sms(self):
        self.state = 'done'
        self.report_date = fields.datetime.now()
        deltatime = (fields.datetime.now() - self.planned_date)
        minutes = divmod(deltatime.total_seconds(), 60)[0] / 60
        self.delay_time = minutes if minutes else 0.0
        return {
            'effect': {
                'fadeout': 'slow',
                'message': 'Good job',
                'type': 'rainbow_man',
            }
        }

    def generate_qr_code(self, id):
        for record in self:
            test_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url') + record.get_portal_url()
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(test_url)
            qr.make(fit=True)
            img = qr.make_image()
            temp = BytesIO()
            img.save(temp, format="PNG")
            qr_image = base64.b64encode(temp.getvalue())
            return qr_image

    @api.onchange('date', 'sample_line')
    def onchange_date(self):
        for record in self:
            if record.sample_line.product_ids:
                planned_date = False
                tat = 0.0
                list_estimated_time = record.sample_line.product_ids.mapped('estimated_time') + (
                    record.sample_line.product_ids.filtered(lambda self: self.isPack == True).child_ids.mapped(
                        'estimated_time'))
                maximum_delay = max(list_estimated_time)
                date_start = record.date.strftime("%Y-%m-%d")
                date_end = (record.date + timedelta(hours=maximum_delay)).strftime("%Y-%m-%d")
                nb_weekend = np.busday_count(date_start, date_end,
                                             weekmask='Fri Sat')
                tat = maximum_delay + nb_weekend * 24
                planned_date = record.date + timedelta(hours=maximum_delay + nb_weekend * 24)
                if datetime.date(planned_date).weekday() == 4:
                    planned_date = planned_date + timedelta(2)
                    tat += 48
                # add the weekend to tat
                record.tat = tat
                record.planned_date = planned_date
            else:
                record.tat = 0.0

    def _get_valid_analysis(self):
        return self.analysis_ids.filtered(lambda a: a.state != 'cancel')

    @api.depends('analysis_ids')
    def _get_analysis(self):
        for order in self:
            analysis = order._get_valid_analysis()
            if analysis:
                order.analysis_count = len(analysis)
            else:
                order.analysis_count = 0

    @api.depends('analysis_ids')
    def _compute_analysis_done(self):
        for order in self:
            if order.analysis_ids and all(analysis.state == 'valid' for analysis in order.analysis_ids):
                order.date_done = fields.datetime.now()
                order.analysis_done = True
            else:
                order.analysis_done = False

    def _compute_access_url(self):
        super(Lims_sample, self)._compute_access_url()
        for request in self:
            request.access_url = '/my/requests/%s' % (request.id)

    def preview_analysis_report(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'target': 'self',
            'url': self.get_portal_url(),
        }

    def _get_report_base_filename(self):
        self.ensure_one()
        return '%s %s' % (self.name, self.partner_id.name)

    def _get_portal_return_action(self):
        """ Return the action used to display orders when returning from customer portal. """
        self.ensure_one()
        return self.env.ref('lims.receiving_samples_action')

    def action_view_analysis(self):
        analysis_ids = self.mapped('analysis_ids')
        action = self.env["ir.actions.actions"]._for_xml_id("lims.analysis_action")
        if len(analysis_ids) > 1:
            action['domain'] = [('id', 'in', analysis_ids.ids)]
        elif len(analysis_ids) == 1:
            form_view = [(self.env.ref('lims.lims_analysis_view_form').id, 'form')]
            if 'views' in action:
                action['views'] = form_view + [(state, view) for state, view in action['views'] if view != 'form']
            else:
                action['views'] = form_view
            action['res_id'] = analysis_ids.id
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

    def action_view_sale_order(self):
        sale_id = self.mapped('sale_id')
        action = self.env["ir.actions.actions"]._for_xml_id("sale.action_quotations_with_onboarding")
        if len(sale_id):
            form_view = [(self.env.ref('sale.view_order_form').id, 'form')]
            if 'views' in action:
                action['views'] = form_view + [(state, view) for state, view in action['views'] if view != 'form']
            else:
                action['views'] = form_view
            action['res_id'] = sale_id.id
        else:
            action = {'type': 'ir.actions.act_window_close'}

        context = {
            'default_company_id': self.env.company.id,
        }
        if len(self) == 1:
            context.update({
                'default_partner_id': self.partner_id.id,
                'default_origin': self.name,
                'default_user_id': self.user_id.id,
            })
        action['context'] = context
        return action

    def action_view_invoice(self):
        invoices = self.mapped('invoice_ids')
        action = self.env["ir.actions.actions"]._for_xml_id("account.action_move_out_invoice_type")
        if len(invoices) > 1:
            action['domain'] = [('id', 'in', invoices.ids)]
        elif len(invoices) == 1:
            form_view = [(self.env.ref('account.view_move_form').id, 'form')]
            if 'views' in action:
                action['views'] = form_view + [(state, view) for state, view in action['views'] if view != 'form']
            else:
                action['views'] = form_view
            action['res_id'] = invoices.id
        else:
            action = {'type': 'ir.actions.act_window_close'}

        context = {
            'default_company_id': self.env.company.id,
        }
        if len(self) == 1:
            context.update({
                'default_partner_id': self.partner_id.id,
                'default_origin': self.name,
                'default_user_id': self.user_id.id,
            })
        action['context'] = context
        return action

    def action_sale_order_print(self):
        # if self.user_has_groups('lims.group_lims_manager'):
        return self.env.ref('sale.action_report_saleorder').report_action(self.sale_id)

    def reset_to_draft(self):
        self.state = 'draft'

    def do_recieve(self):
        for s in self.sample_line_prepared:
            s.do_received()
        self.state = 'recieved'
        self.receiving_date = fields.datetime.now()

    def do_validate(self):
        for record in self:
            if not record.analysis_done:
                raise UserError(_("Sorry,all tests must be completed"))
            else:
                # user_group = record.env.ref("lims.group_lims_manager")
                # for user in user_group.users:
                # 	data = {
                # 			'res_id': record.id,
                # 			'res_model_id': record.env['ir.model'].search([('model', '=', 'lims.sample.main')]).id,
                # 			'user_id': user.id,
                # 			'summary': 'Folder %s  need your validation' % record.name,
                # 			'activity_type_id': record.env.ref('lims.activity_analysis_report').id,
                # 			# 'date_deadline': date_deadline
                # 			}
                # 	record.env['mail.activity'].create(data)
                record.signature_director = record.env.company.signature_director
            record.state = 'tosend'

    def action_reject(self):
        return {
            'name': _('Reason'),
            'type': 'ir.actions.act_window',
            'res_model': 'add.reason.wizard',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_main_id': self.id}
        }

    def do_reject(self):
        if self.env.user.has_group('lims.group_lims_manager'):
            analysis_ids = self.env['lims.analysis'].search([('main_id', '=', self.id)])
            for a in analysis_ids:
                a.do_reject()
            for s in self.sample_line_prepared:
                s.do_cancel()
            self.sale_id._action_cancel() if self.sale_id else False
            invoice = self.invoice_ids.filtered(lambda inv: inv.invoice_origin == self.sale_id.name)
            invoice.button_cancel() if invoice else False
            return self.write({'state': 'reject',
                               'sale_id': False})
        else:
            raise UserError("You have not access to reject this request")

    def action_confirm(self):
        if not len(self.sample_line):
            raise UserError("Please add the requested test(s) before confirming this request")
        self.state = 'confirm'
        self.qrcode = self.generate_qr_code(self.id)
        if self.sale_id:
            self.sale_id.qrcode = self.qrcode

    # def explode_pack(self, lista, sample_type_id, partner_id):
    #     if len(lista) == 0:
    #         return []
    #     else:
    #         p = self.env['product.product'].search([('id', '=', lista[0])], limit=1)
    #         if p.isPack:
    #             products = self.env['product.product'].search([('product_tmpl_id', 'in', p.child_ids.ids)])
    #             lista.pop(0)
    #             lista += products.ids
    #             res = []
    #         else:
    #             res = [(p.id, sample_type_id if sample_type_id else p.default_sample_type.id, p.collection_tube.id,
    #                     partner_id.id)]
    #             if self.env.company.split_sample_by_department:
    #                 res = [(p.id, sample_type_id if sample_type_id else p.default_sample_type.id,
    #                         p.collection_tube.id, partner_id.id, p.department_id)]
    #             lista.pop(0)
    #         res += self.explode_pack(lista, sample_type_id, partner_id)
    #         return res

    # def _prepare_sample_vals(self, product_list, keys):

    #     res = []
    #     for k, lines in itertools.groupby(product_list, key=keys):
    #         product_ids = []
    #         collection_date = None

    #         for item in lines:
    #             product_ids.append(item[1])
    #             collection_date = item[0].external_sample_collected_on

    #         department_id = k[-1] if self.env.company.split_sample_by_department else False
    #         res.append({
    #             'sample': k[0],
    #             'product_ids': [(6, 0, product_ids)],
    #             'partner_id': k[2],
    #             'date': datetime.now(),
    #             'main_id': self.id,
    #             'company_id': self.company_id.id,
    #             'note': '',
    #             'sample_date': collection_date,
    #             'prefix': department_id.prefix_code if department_id else '',
    #             'state': 'todo',
    #             'laboratory_id': self.laboratory_id.id
    #         })
    #     return res

    # def _create_sample(self, product_list, keys):
    #     res = []
    #     vals = self._prepare_sample_vals(product_list, keys)
    #     for val in vals:
    #         new_record = self.env['lims.sample.preparation'].create(val)
    #         res.append(new_record)
    #     return res

    def generate_samples(self):
        return {}

    #     res = []
    #     product_list = []

    #     # Collect products from each sample line
    #     for sample in self.sample_line:
    #         quantity = int(sample.quantity)
    #         product_ids = sample.mapped('product_ids').ids
    #         sample_id = sample.sample.id
    #         partner_id = sample.partner_id
    #         for _ in range(quantity):
    #             pre_list = self.explode_pack(product_ids, sample_id, partner_id)
    #             product_list += [tuple(sample) + e for e in pre_list]

    #     # Define sorting keys based on company settings
    #     if self.env.company.split_sample_by_department:
    #         keys = lambda x: (x[2], x[3], x[4], x[5])
    #     else:
    #         keys = lambda x: (x[2], x[3], x[4])

    #     # Sort the product list
    #     product_list = sorted(product_list, key=keys)

    #     # Group products and create sample preparation records
    #     res = self._create_sample(product_list, keys)
    #     return res

    @api.model
    def _prepare_analysis_line(self, sample, parameter, pack, **kwargs):
        return {}

    #     department_id = parameter.department_ids.filtered(lambda d: d.laboratory_id.id == self.laboratory_id.id)
    #     vals = {'main_id': self.id,
    #             'pack_selected': pack if pack else False,
    #             'sample': sample.sample.id,
    #             'department_id': department_id.id if department_id else False,
    #             'laboratory_id': sample.laboratory_id.id,
    #             'product_id': parameter.id,
    #             'partner_id': sample.partner_id.id,
    #             'sample_line_id': sample.id,
    #             'company_id': self.company_id.id
    #             }
    #     if sample.partner_id.id == self.partner_id.id:
    #         vals.update({'index_analysis': True})
    #     return vals

    def generate_analysis(self):
        return {}

    #     sample_line_prepared = self.mapped('sample_line_prepared').filtered(lambda a: a.state == 'recieved')
    #     if self.invoicing_type == 'foc' and not self.approved_foc:
    #         raise UserError("Please contact your manager to approve Free Of charge request")
    #     if len(sample_line_prepared):
    #         analysis_ids_vals = []
    #         pack = False
    #         for sample in sample_line_prepared:
    #             # sample.sample_date = fields.datetime.now()
    #             for product in sample.product_ids:
    #                 if product not in self.analysis_ids.filtered(lambda a: a.state != 'cancel' and
    #                                                                        a.sample_line_id.id == sample.id).mapped(
    #                     'product_id'):
    #                     if len(product.parent_pack.ids):
    #                         for p in product.parent_pack:
    #                             pack = p.id if p.id in self.sample_line.mapped('product_ids').ids else False
    #                             if pack:
    #                                 break
    #                     # pack = product.parent_pack if product.parent_pack and product.parent_pack.id in self.sample_line.mapped('product_ids').ids else False
    #                     analysis_ids_vals.append((0, 0, self._prepare_analysis_line(sample, product, pack)))
    #                     sample.receiving_date = fields.datetime.now()
    #         if analysis_ids_vals:
    #             return self.update({'analysis_ids': analysis_ids_vals,
    #                                 'state': 'progress'})
    #         else:
    #             raise UserError('Please check the following: \n The requested tests are already created \n'
    #                             'Contact your administrator')
    #     else:
    #         raise UserError('Please click accept sample before create analysis')

    def _prepare_sale_order_values(self, partner):
        return {'partner_id': partner.id,
                'partner_invoice_id': partner.id,
                'partner_shipping_id': partner.id,
                'date_order': self.date,
                'commitment_date': self.planned_date,
                'origin': self.name,
                'user_id': self.env.user.id,
                'fiscal_position_id': partner.property_account_position_id.id,
                'currency_id': partner.property_product_pricelist.currency_id.id,
                'company_id': self.company_id.id,
                'pricelist_id': partner.property_product_pricelist.id if partner.property_product_pricelist else False

                }

    def _create_sale_order(self):
        order_line_vals = []
        partner_id = self.partner_id
        vals = self._prepare_sale_order_values(partner_id)
        for item in self.sample_line:
            if item.description:
                order_line_vals.append((0, 0, {
                    'display_type': 'line_section',
                    'name': item.description,
                }))
            for parameter in item.product_ids:
                if not parameter.finance_validated:
                    raise ValidationError(
                        f"{parameter.name} is not financially validated. Please validate before proceeding.⚠️")
                taxes = parameter.taxes_id.filtered(lambda t: t.company_id == self.env.company)
                fpos = self.partner_id.property_account_position_id
                order_line_vals.append((0, 0, {
                    'product_id': parameter.id,
                    'name': parameter.description_sale or parameter.name,
                    'product_uom_qty': item.quantity,
                    'discount': 0.0,
                    'qty_delivered': item.quantity,
                    'product_uom': parameter.uom_id.id,
                    'price_unit': parameter.lst_price,
                    'customer_lead': parameter.estimated_time,
                    'tax_id': fpos.map_tax(taxes),
                    'company_id': self.company_id.id,
                    'display_type': False,
                }))

        vals.update({'order_line': order_line_vals})
        res = self.env['sale.order'].create(vals)
        if res:
            res.sudo()._recompute_taxes()
            res.sudo().action_update_prices()
        return res

    def generate_sale_order(self):
        if len(self.sample_line):
            if self.sale_id:
                self.sale_id.action_cancel()
                self.reset_to_draft()
            if self.invoicing_type == 'quot':
                self.sale_id = self._create_sale_order().id
                return self.action_view_sale_order()
            elif self.invoicing_type == 'invoice':
                self.sale_id = self._create_sale_order().id
                self.sale_id.action_confirm()
                res = self.sale_id.sudo()._create_invoices() if self.sale_id else False
                res.main_id = self.id
                res.laboratory_id = self.laboratory_id.id
                res.action_post()
                self.action_confirm()
                return self.action_view_invoice()
            else:
                pass
        else:
            raise UserError(_(
                'Please fill your request line, then clic generate quotation'
            ))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if 'company_id' in vals:
                self = self.with_company(vals['company_id'])
            if not vals.get('name') or vals['name'] == _('New'):
                lab_id = vals.get('laboratory_id') or self.env.user.default_laboratory_id.id
                seq_date = None
                if 'date' in vals:
                    seq_date = fields.Datetime.context_timestamp(self, fields.Datetime.to_datetime(vals['date']))
                vals['name'] = _next_lab_seq(self.env, 'lims.sample.main', lab_id, seq_date)
            result = super(Lims_sample, self).create(vals)
            return result

    def unlink(self):
        for order in self:
            if order.state not in ('draft', 'reject'):
                raise UserError(_('You can not delete a confirmed analysis folder. You must cancel it first.'))
        return super(Lims_sample, self).unlink()

    def action_report_print(self):
        # if self.user_has_groups('lims.group_lims_manager'):
        return self.env.ref('lims.medical_lab_analysis_report').report_action(self)

    def action_report_print_all_label(self):
        # if self.user_has_groups('lims.group_lims_manager'):
        return self.env.ref('lims.medical_lab_label_all').report_action(self)


class Lims_sampleLine(models.Model):
    _name = 'lims.sample.line'
    _description = "Requested Tests"

    name = fields.Char('Sample Code', )
    product_ids = fields.Many2many('product.product', string='Test/Pack',
                                   required=True)
    sample = fields.Many2one('lims.sample.type', string='Sample type', required=False)
    uom_id = fields.Many2one('uom.uom', related='sample.uom_id')
    quantity = fields.Float('Quantity', required=True, default=1)
    main_id = fields.Many2one('lims.sample.main', 'Request')
    date = fields.Datetime('Date', related='main_id.date')
    partner_id = fields.Many2one('res.partner', 'Customer')
    check = fields.Boolean('Well recieved', default=False, copy=False)
    note = fields.Char('Note')
    description = fields.Char('Description')
    external_sample_collected_on = fields.Datetime("Sample collected on", help="External sample collected on")
    lock = fields.Boolean(string='Lock', default=False,
                          help='Lock request so that further'
                               ' modifications are not possible.')
    unlock_datetime = fields.Datetime("Unlock Datetime")
    unlock_reason = fields.Char("Unlock reason")

    @api.onchange('date', 'partner_id')
    def onchange_description(self):
        name = ''
        if self.partner_id:
            name += self.partner_id.name
        if self.date:
            name += '/' + str(self.date)
        self.name = name

    @api.model_create_multi
    def create(self, vals):
        result = super(Lims_sampleLine, self).create(vals)
        if 'partner_id' in vals:
            raise UserError("Please select the partner at the request line level")
        return result

    @api.constrains('product_ids')
    def _check_product_validated(self):
        for record in self:
            invalid_products = record.product_ids.filtered(lambda p: not p.lab_validated)
            if invalid_products:
                names = ", ".join(invalid_products.mapped('name'))
                raise ValidationError(
                    f"The following parameters are not validated: {names}. Please validate them before saving."
                )


class Lims_sample_preparation(models.Model):
    _name = 'lims.sample.preparation'
    _description = "Samples Information"
    _order = 'name desc, sample_date desc'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'sequence.mixin', 'utm.mixin']
    _rec_name = 'name'

    @api.depends('product_ids')
    def get_max_volume(self):
        for record in self:
            if record.product_ids:
                res = max(parameter.optimum_volume for parameter in record.product_ids)
                record.optimum_volume = res
                return res
            else:
                return 0.0

    # @api.depends('name', 'prefix')
    # def get_display_name(self):
    #     for record in self:
    #         if record.prefix:
    #             record.display_name = record.prefix + '-' + record.name
    #         else:
    #             record.display_name = record.name

    name = fields.Char('Sample code', default='New', index=True)
    product_ids = fields.Many2many('product.product', domain=[('type', '=', 'service')], string='Test/Parameter')
    sample = fields.Many2one('lims.sample.type', string='Sample')
    uom_id = fields.Many2one('uom.uom', related='sample.uom_id')
    main_id = fields.Many2one('lims.sample.main', 'Request', required=True)
    date = fields.Datetime('Date', tracking=True)
    partner_id = fields.Many2one('res.partner', 'Customer')
    check = fields.Boolean('Well recieved', default=False, copy=False)
    note = fields.Char('Note')
    analysis_ids = fields.One2many('lims.analysis', 'sample_line_id', 'Analysis')
    qrcode = fields.Binary('QRcode', attachment=True, store=True)
    state = fields.Selection(
        [('todo', 'To receive'), ('recieved', 'Received'), ('prepared', 'Prepared'), ('progress', 'In-progress'),
         ('blocked', 'Blocked'), ('cancel', 'Canceled')],
        default='todo')
    sample_date = fields.Datetime('Collected Sample Date', tracking=True)
    subsample_ids = fields.One2many('lims.sub.sample.preparation', 'sample_id', 'Sub-Samples')
    nb_sub = fields.Integer('Nb Sub-samples')
    user_id = fields.Many2one('res.users', 'Collector')
    optimum_volume = fields.Float(compute='get_max_volume', store=True)
    prefix = fields.Char('Prefix code')
    # display_name = fields.Char('Label Code', compute='get_display_name')
    receiving_date = fields.Datetime("Received on")
    sending_date = fields.Datetime("Sample Sending Date")
    company_id = fields.Many2one('res.company', 'company', default=lambda self: self.env.company.id)
    laboratory_id = fields.Many2one("lims.laboratory", "Laboratory", required=True,
                                    default=lambda self: self.env.user.default_laboratory_id.id)
    lock = fields.Boolean(string='Lock', default=False,
                          help='Lock request so that further'
                               ' modifications are not possible.')
    unlock_datetime = fields.Datetime("Unlock Datetime", tracking=True)
    unlock_reason = fields.Char("Unlock reason", tracking=True)

    def do_cancel(self):
        return {
            'name': _('Reason'),
            'type': 'ir.actions.act_window',
            'res_model': 'add.reason.wizard',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_sample_id': self.id}
        }

    def do_received(self):
        self.state = 'recieved'
        self.lock = True,
        if not self.receiving_date:
            self.receiving_date = fields.datetime.now()
            # create analysis after accepting sample
        # self.create_analysis()
        if all(s.state == 'recieved' for s in self.main_id.sample_line_prepared):
            self.main_id.write({'state': 'recieved', 'lock': True})
            for line in self.main_id.sample_line:
                line.lock = True

        self.user_id = self.env.user.id
        return False

    def onchange_qrcode(self):
        for record in self:
            if record.state == 'todo':
                self.sudo().write({'qrcode': self.generate_qr_code(self.id)})
            # self.main_id.state = 'recieved'

    def reset_todo(self):
        for record in self:
            record.state = 'todo'
            record.main_id.state = 'confirm'

    @api.model_create_multi
    def create(self, values):
        for vals in values:
            lab_id = vals.get('laboratory_id') or self.env.user.default_laboratory_id.id
            seq_date = None
            if vals.get('date'):
                seq_date = fields.Datetime.context_timestamp(self, fields.Datetime.to_datetime(vals['date']))
            vals['name'] = _next_lab_seq(self.env, 'lims.sample.preparation', lab_id, seq_date)
        result = super(Lims_sample_preparation, self).create(values)
        result.onchange_qrcode()
        return result

    def action_report_print(self):
        return self.env.ref('lims.medical_lab_label').report_action(self)

    def print_pdf(self):
        pdf = self.env['report'].get_pdf(self, 'lims.medical_lab_label')
        if pdf:
            return {'data': pdf.encode('base64'), 'name': self.name}
        else:
            return {'error': 'Attachment not found', 'name': self.name}

    def generate_qr_code(self, id):
        for record in self:
            # test_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')+record.main_id.get_portal_url()
            # print(request.httprequest.__dict__)
            data = 'Sample Code: ' + str(record.name) + '\n'
            data += 'File ID: ' + str(record.main_id.name) + '\n' + 'Customer: ' + str(record.partner_id.name) + '\n'
            date = fields.Datetime.context_timestamp(record, fields.Datetime.to_datetime(record.date))
            data += 'Sample Type: ' + str(record.sample.name) + '\n' + 'Sampling date: ' + date.strftime(
                "%m/%d/%Y, %H:%M") + '\n' + 'Analysis:\n'
            # raise UserError(_())
            for p in record.product_ids:
                data += str(p.name if p else '') + '\n'
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(data)
            qr.make(fit=True)
            img = qr.make_image()
            temp = BytesIO()
            img.save(temp, format="PNG")
            qr_image = base64.b64encode(temp.getvalue())
            return qr_image

    def generate_sub_samples(self):
        iter = len(self.subsample_ids) + 1
        for s in range(self.nb_sub):
            if len(self.subsample_ids) >= self.nb_sub:
                break
            else:
                vals = {'sample_id': self.id,
                        'sequence': iter
                        }
                iter += 1
                self.env["lims.sub.sample.preparation"].create(vals)

    def add_parameters(self):
        return {
            'name': _('ADD PARAMETERS'),
            'type': 'ir.actions.act_window',
            'res_model': 'add.parameters.wizard',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_line_id': self.id}
        }

    # def create_analysis(self):
    #     for sample in self.filtered(lambda self: self.state == 'recieved'):
    #         main_id = sample.main_id
    #         analysis_ids_vals = []
    #         pack = False
    #         for product in sample.parameter_ids:
    #             if product not in main_id.analysis_ids.filtered(lambda a: a.state != 'cancel').mapped('product_id'):
    #                 if len(product.parent_pack.ids):
    #                     for p in product.parent_pack:
    #                         pack = p.id if p.id in main_id.sample_line.mapped('product_ids').ids else False
    #                         if pack:
    #                             break
    #                 # pack = product.parent_pack if product.parent_pack and product.parent_pack.id in self.sample_line.mapped('product_ids').ids else False
    #                 analysis_ids_vals.append((0, 0, main_id._prepare_analysis_line(sample, product, pack)))
    #         if analysis_ids_vals:
    #             sample.receiving_date = fields.datetime.now()
    #             return main_id.update({'analysis_ids': analysis_ids_vals,
    #                                    'state': 'progress'})

    def create_analysis(self):
        # SampleMain = self.env['lims.sample.main']

        # for rec in self:
        #     # get existing parameters already in analyses
        #     existing_parameters = rec.analysis_ids.mapped('product_id')
        #     new_parameters = rec.parameter_ids - existing_parameters

        #     analysis_vals = []

        #     for parameter in new_parameters:
        #         # detect package if parameter comes from one
        #         pack = rec.product_ids.filtered(
        #             lambda p: p.isPack and parameter in p.child_ids.mapped('product_variant_ids'))
        #         pack = pack[0] if pack else False

        #         # reuse helper from lims.sample.main
        #         vals = SampleMain._prepare_analysis_line(
        #             sample=rec,
        #             parameter=parameter,
        #             pack=pack
        #         )
        #         analysis_vals.append((0, 0, vals))  # <-- (0,0,vals) for One2many

        #     if analysis_vals:
        #         # update the One2many directly and change state
        #         rec.write({
        #             'analysis_ids': analysis_vals,
        #             'state': 'progress'
        #         })
        return {}


class Lims_sub_sample_preparation(models.Model):
    _name = 'lims.sub.sample.preparation'
    _description = "Samples"

    sample_id = fields.Many2one("lims.sample.preparation", "Main Sample")
    name = fields.Char('Code', readonly=True, index=True)
    sequence = fields.Char('Sequence', readonly=True)
    amount = fields.Float('Amount')
    uom_id = fields.Many2one('uom.uom', related='sample_id.uom_id')
    date = fields.Datetime('Date', default=lambda self: fields.datetime.now())

    def name_get(self):
        result = []
        for rec in self: result.append((rec.id, '%s-%s' % (rec.sample_id.name, rec.sequence)))
        return result

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == _('New'):
                # Derive lab from the parent sample
                lab_id = None
                if vals.get('sample_id'):
                    sample = self.env['lims.sample.preparation'].browse(vals['sample_id'])
                    lab_id = sample.laboratory_id.id
                lab_id = lab_id or self.env.user.default_laboratory_id.id
                seq_date = None
                if vals.get('date'):
                    seq_date = fields.Datetime.context_timestamp(self, fields.Datetime.to_datetime(vals['date']))
                vals['name'] = _next_lab_seq(self.env, 'lims.sub.sample.preparation', lab_id, seq_date)
        return super(Lims_sub_sample_preparation, self).create(vals_list)

    def action_report_print(self):
        return self.env.ref('lims.medical_lab_label').report_action(self)


class AddParameters(models.TransientModel):
    _name = 'add.parameters.wizard'
    _description = 'Add Parameter'

    line_id = fields.Many2one('lims.sample.preparation', 'Preparation line', readonly=True)
    product_ids = fields.Many2many('product.product', string="New Parameters")
    domain_products = fields.Char(compute='onchange_product_domain', store=False, readonly=True)

    def generate_test(self):
        for p in self.product_ids:
            self.line_id.product_ids = [(4, p.id)]

    @api.depends('product_ids')
    def onchange_product_domain(self):
        for rec in self:
            rec.domain_products = json.dumps(
                [('default_sample_type', '=', rec.line_id.sample.id)]) if rec.line_id.sample else "[]"
