# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import json
from datetime import datetime, timedelta
from odoo import api, fields, models, _
from odoo.exceptions import UserError


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
        ctx = {'ir_sequence_date': seq_date} if seq_date else {}
        return seq.with_context(**ctx)._next()
    return env['ir.sequence'].next_by_code(code, sequence_date=seq_date) or _('New')


class LimsAnalysis(models.Model):
    _name = 'lims.analysis'
    _description = 'Tests'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'sequence.mixin']
    _order = 'date desc, date_result desc'

    def _default_factor(self):
        return self.env.ref('lims.default_rang_factor', False)

    @api.depends('name', 'product_id')
    def _compute_display_name(self):
        for record in self:
            product_name = record.product_id.name or ''
            base_name = record.name or ''
            record.display_name = f"{base_name} - {product_name}" if product_name else base_name

    display_name = fields.Char(string="Display Name", compute='_compute_display_name', store=True)
    latitude = fields.Float(string="Latitude", related='partner_id.partner_latitude', store=True)
    longitude = fields.Float(string="Longitude", related='partner_id.partner_longitude', store=True)
    name = fields.Char('Analysis Number', default='New', index=True)
    date = fields.Datetime('Date start', tracking=True)
    date_result = fields.Datetime('Date result', tracking=True, copy=False, readonly=True)
    main_id = fields.Many2one('lims.sample.main', 'Request', readonly=True)
    sample = fields.Many2one('lims.sample.type', string='Sample type', readonly=True)
    sample_line_id = fields.Many2one('lims.sample.preparation', 'Sample', readonly=True, index=True)
    product_id = fields.Many2one('product.product', domain=[('type', '=', 'service'), ('isParameter', '=', True)],
                                 string='Test/Parameter')
    method_id = fields.Many2one('lims.method', string='Method')
    type_result = fields.Selection(related='product_id.type_result', string="Result Type")
    result_se = fields.Many2one('lims.result', string='Selection Result', tracking=True, copy=False)
    result_num = fields.Float('Numerical Result', tracking=True, copy=False, digits=(12, 4))
    result_txt = fields.Char('Result', tracking=True, copy=False)
    uom_id = fields.Many2one('uom.uom')
    user_id = fields.Many2one('res.users', string='Responsible', tracking=True, domain=[('share', '=', False)])
    note = fields.Char('Note', tracking=True)
    state = fields.Selection(
        [('draft', 'Draft'), ('todo', 'ToDo'), ('progress', 'In progress'), ('rework', 'Rework'), ('done', 'Done'),
         ('valid', 'Validated'), ('cancel', 'Canceled')], default='draft', tracking=True)
    department_id = fields.Many2one('lims.department', 'Department', store=True)
    company_id = fields.Many2one('res.company', 'company', default=lambda self: self.env.company.id)
    partner_id = fields.Many2one('res.partner', 'Customer', tracking=True)
    reason_id = fields.Many2one('lims.reason.type', 'Reason', tracking=True, readonly=True)
    hide_result = fields.Boolean('Hide result', compute='_compute_hide_result')
    state_result = fields.Selection(
        [('default', 'Inconclusive'), ('normal', 'Normal'), ('oor', 'Abnormal'), ('low', 'Low'), ('hight', 'High')],
        compute='_get_result_state')
    pack_selected = fields.Many2one('product.product', domain=[('isPack', '=', 'True')])
    factor_id = fields.Many2one('lims.rang.factor', 'Factor', default=_default_factor)
    domain_result = fields.Char(compute='onchange_type_result', store=False, readonly=True)
    domain_method = fields.Char(compute='onchange_method_domain', store=False, readonly=True)
    is_null = fields.Boolean('Is Null')
    history_ids = fields.One2many('lims.result.history', 'analysis_id', 'Results History', readonly=True)
    last_old_result = fields.Char('Previous Result', tracking=True, copy=False)
    is_subcontracted = fields.Boolean('Subcontracted Test')
    validated_by = fields.Many2one('res.users', 'Validated by', readonly=True, copy=False)
    validated_on = fields.Datetime("Validation Date", readonly=True, copy=False)
    index_analysis = fields.Boolean("Index Analysis")
    laboratory_id = fields.Many2one("lims.laboratory", "Laboratory", required=True,
                                    default=lambda self: self.env.user.default_laboratory_id.id)
    assign_date = fields.Datetime("Responsible assign date")

    @api.onchange('product_id', 'method_id')
    def onchange_product_uom(self):
        reference = self.get_references() if self.method_id else False
        res = reference[0] if reference else False
        self.uom_id = res.uom_id.id if res else self.product_id.uom_id.id

    def _get_reference_domain(self):
        for record in self:
            res = lambda r: r.product_id.id == record.product_id.product_tmpl_id.id
        return res

    def get_references(self):
        rang_result = False
        for record in self:
            rang_result = record.method_id.reference_ids.filtered(self._get_reference_domain())
        return rang_result

    @api.depends('method_id', 'uom_id', 'result_num')
    def _get_result_state(self):
        for record in self:
            status = 'default'
            rang_result = record.get_references()
            if record.type_result == 'num':
                if len(rang_result):
                    for rang in rang_result:
                        if record.uom_id == rang.uom_id and rang.status.code == 'OK':
                            if record.result_num < rang.min_val:
                                status = 'low'
                            elif record.result_num > rang.max_val:
                                status = 'hight'
                            else:
                                status = 'normal'
                            break
                        else:
                            status = 'default'
                else:
                    status = 'default'
            elif record.type_result == 'se':
                if record.result_se.state.code == 'OK':
                    status = 'normal'
                else:
                    record.state_result = 'oor'
            else:
                status = 'default'

            record.state_result = status

    @api.depends('product_id')
    def onchange_type_result(self):
        for rec in self:
            product = rec.product_id
            rec.domain_result = json.dumps([('id', 'in', product.se_results.ids)]) if product.se_results else "[]"

    @api.depends('product_id')
    def onchange_method_domain(self):
        for rec in self:
            product = rec.product_id
            rec.domain_method = json.dumps([('id', 'in', product.method_ids.ids)]) if product.method_ids else "[]"

    @api.onchange('result_se', 'result_num', 'uom_id')
    def onchange_text_result(self):
        self.result_txt = ''

        if self.result_num and not self.is_null:
            decimals = self.product_id.nb_decimal or 0

            # Format only for display (no impact on stored value)
            if decimals == 0:
                value_str = str(int(self.result_num))
            else:
                value_str = f"{self.result_num:.{decimals}f}"

            self.result_txt = value_str

            if self.uom_id:
                self.result_txt += f" {self.uom_id.name}"

        elif self.result_se:
            self.result_txt = self.result_se.name

        else:
            self.result_txt = "Null"

    @api.depends('state')
    def _compute_hide_result(self):
        for record in self:
            record.hide_result = True if record.state in ('draft', 'todo') else False

    @api.model_create_multi
    def create(self, vals_list):
        # if 'sample_line_id' not in vals:
        #     raise UserError('Cannot create analysis without sample')
        for vals in vals_list:
            if 'company_id' in vals:
                self = self.with_company(vals['company_id'])
            if not vals.get('name') or vals['name'] == _('New'):
                lab_id = vals.get('laboratory_id') or self.env.user.default_laboratory_id.id
                seq_date = None
                if vals.get('date'):
                    seq_date = fields.Datetime.context_timestamp(self, fields.Datetime.to_datetime(vals['date']))
                vals['name'] = _next_lab_seq(self.env, 'lims.analysis', lab_id, seq_date)
            result = super(LimsAnalysis, self).create(vals)
            default_methods = result.product_id.method_ids.filtered(lambda m: m.is_default == True)
            if len(default_methods):
                result['method_id'] = default_methods.ids[0]
            if result.product_id.type_result == 'txt':
                result.result_txt = '/'
        return result

    def unlink(self):
        for order in self:
            if order.state not in ('draft', 'cancel'):
                raise UserError(_('You can not delete a confirmed analysis test. You must first cancel it.'))
        return super(LimsAnalysis, self).unlink()

    def do_confirm(self):
        for record in self:
            notification_ids = []
            if not record.user_id:
                raise UserError(_(
                    'You must select the responsible for this analysis'
                ))
            else:
                data = {
                    'res_id': record.id,
                    'res_model_id': self.env['ir.model'].sudo().search([('model', '=', 'lims.analysis')]).id,
                    'user_id': record.user_id.id,
                    'summary': 'Analysis %s has been assigned to you' % record.name,
                    'activity_type_id': self.env.ref('lims.activity_analysis').id,
                    'date_deadline': record.main_id.planned_date if record.main_id.planned_date else record.main_id.date + timedelta(
                        days=7)
                }
                self.env['mail.activity'].create(data)
                self.onchange_product_uom()
                record.state = 'todo'
                record.assign_date = fields.Datetime.now()

    def action_confirm(self):
        if self._context.get('active_model') == 'lims.analysis' and self._context.get('active_id', False):
            analysis = self.env['lims.analysis'].browse(self._context.get('active_id'))
            for a in analysis:
                a.do_confirm()

    def do_work(self):
        if self.department_id.id in self.env.user.department_ids.ids and (
                self.env.user.has_group('lims.group_lims_analysis') \
                or self.env.user.has_group('lims.group_lims_responsible')):
            self.state = 'progress'
            self.main_id.state = 'progress'
            self.date = fields.Datetime.now()

    def do_done(self):
        for record in self:
            if (
                    record.department_id.id in record.env.user.department_ids.ids
                    and record.env.user.has_group('lims.group_lims_analysis')
            ):
                if (not record.result_se and not record.result_num and not record.is_null and not record.result_txt):
                    raise UserError(_('Please insert the result before confirming'))
                is_detected = (record.result_se and record.result_se.name in ['Detected', 'تم الكشف'])
                if is_detected and not record.component_ids:
                    raise UserError(_(
                        "You cannot confirm this analysis because the result is 'Detected', Please add pesticide components before confirming."
                    ))

                activity = record.env['mail.activity'].sudo().search([
                    ('res_model', '=', 'lims.analysis'),
                    ('res_id', '=', record.id),
                    ('user_id', '=', record.user_id.id),
                    ('activity_type_id', '=', record.env.ref('lims.activity_analysis').id),
                ], limit=1)

                if activity:
                    activity.action_feedback(feedback=_('Analysis %s has been done') % record.name)
                    record.activity_schedule(
                        'lims.activity_analysis_done',
                        summary=_("Analysis to validate"),
                        user_id=record.department_id.manager_id.id
                    )

                record.state = 'done'
                record.date_result = fields.Datetime.now()

            else:
                raise UserError(_("Please check if you have access rights as analyst of this department"))

    # def do_done(self):
    #     for record in self:
    #         if record.department_id.id in record.env.user.department_ids.ids and record.env.user.has_group(
    #                 'lims.group_lims_analysis'):
    #             if not record.result_se and not record.result_num and not record.is_null and not record.result_txt:
    #                 raise UserError(_(
    #                     'Please insert the result before confirming'
    #                 ))

    #             activity = record.env['mail.activity'].sudo().search([
    #                 ('res_model_id', '=', 'lims.analysis'),
    #                 ('res_id', '=', record.id),
    #                 ('user_id', '=', record.user_id.id),
    #                 ('activity_type_id', '=', record.env.ref('lims.activity_analysis').id)
    #             ], limit=1)
    #             if activity:
    #                 # record._update_activity(activity)
    #                 activity.action_feedback(feedback=_('Analysis %s has been done') % (record.name))
    #                 activity = self.activity_schedule(
    #                     'lims.activity_analysis_done',
    #                     summary=_("Analysis to validate"),
    #                     user_id=self.department_id.manager_id.id
    #                 )

    #             record.state = 'done'
    #             record.date_result = datetime.now()
    #         else:
    #             raise UserError("Please check if you have access rights as analyst of this department")

    def update_result(self):
        res = self.env['lims.result.history'].create({
            'name': self.product_id.name,
            'method_id': self.method_id.id,
            'result': self.result_txt,
            'user_id': self.user_id.id,
            'analysis_id': self.id
        })
        res.analysis_id.last_old_result = res.result if res else ""
        return res

    def do_reject(self):
        self.state = 'cancel'
        return self.update_result()

    def do_validate(self):
        for record in self:
            if record.department_id.id in record.env.user.department_ids.ids and record.env.user.has_group(
                    'lims.group_lims_responsible'):
                activity = record.env['mail.activity'].sudo().search([
                    ('res_model_id', '=', 'lims.analysis'),
                    ('res_id', '=', record.id),
                    ('user_id', '=', record.department_id.manager_id.id),
                    ('activity_type_id', '=', record.env.ref('lims.activity_analysis_done').id)
                ], limit=1)
                if activity:
                    # record._update_activity(activity)
                    activity.action_feedback(feedback=_('Analysis %s has been Validated') % (record.name))
            else:
                raise UserError(
                    "Please contact your administrator to check if you have:\n access right as Lab manager for this department")
            record.state = 'valid'
            record.validated_by = record.env.user.id
            record.validated_on = datetime.now()
            return True

    def reset_to_draft(self):
        return self.sudo().write({'state': 'draft', 'date': False,
                                  'date_result': False, 'result_se': False,
                                  'result_num': '', 'result_txt': ''})

    def do_rework(self):
        if self.department_id.id in self.env.user.department_ids.ids and (
                self.env.user.has_group('lims.group_lims_analysis') or \
                self.env.user.has_group('lims.group_lims_responsible')):
            return {
                'name': _('Reason'),
                'type': 'ir.actions.act_window',
                'res_model': 'add.reason.wizard',
                'view_type': 'form',
                'view_mode': 'form',
                'target': 'new',
                'context': {'default_analysis_id': self.id}
            }
        else:
            raise UserError("You have not access to rework a test\nPlease contact your administrator")

    def return_range_txt(self):
        res = ""
        rang_result = self.get_references()
        if rang_result:
            res = ""
            for rang in rang_result:
                if rang.uom_id == self.uom_id and rang.status and rang.status.code == 'OK':
                    splitted_txt = rang.text_rang.split(",")
                    range_list = "<strong>" + str(rang.factor_id.name) + ": </strong>"
                    for s in splitted_txt:
                        range_list += s + "<br/>"

                    res += range_list if range_list else ""
                    continue
                else:
                    res += ""
        else:
            res += ""
        return res

    def convert_to_subcontracted(self):
        return {
            'name': _('Tests to subcontract'),
            'type': 'ir.actions.act_window',
            'res_model': 'convert.subcontracted.wizard',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_analysis_ids': self.ids}
        }

    # def get_timming(self):

    def convert_inhouse(self):
        for record in self:
            department = record.product_id.department_ids.filtered(
                lambda d: d.laboratory_id == record.laboratory_id
            )[:1]
            record.department_id = department.id
            record.is_subcontracted = False
            return {
                'warning': {
                    'title': 'Warning!',
                    'message': "Please don't forget to update the method of this test"}

            }

    def write(self, vals):
        res = super(LimsAnalysis, self).write(vals)
        if self.env.company.auto_done and (
                vals.get('result_num', False) or vals.get('result_se', False)) and not self.is_calculated:
            self.onchange_text_result()
            if all(s in ['todo', 'draft'] for s in [self.state, vals.get('state', False)]):
                self.do_work()
            if self.step_ids and self.step_ids.filtered(lambda s: s.state in ('wip', 'done')):
                raise UserError("Analysis steps are pending for %s - %s , "
                                "please validate it before inserting the finale results" % (
                                    self.sample_line_id.name, self.product_id.name))
            self.do_done()
        if vals.get('user_id', False) and self.state in ['done', 'valid']:
            vals['user_id'] = self.user_id.id
        return res


class ConvertSubcontractedWizard(models.TransientModel):
    _name = 'convert.subcontracted.wizard'
    _description = 'Convert in-house test to subcontracted'

    subcontractor_id = fields.Many2one('lims.department', 'Subcontractor', domain=[('is_subcontractor', '=', True)],
                                       required=True)
    analysis_ids = fields.Many2many('lims.analysis', string='Analysis')

    @api.onchange('subcontractor_id')
    def onchange_subcontractor(self):
        for a in self.analysis_ids:
            a.is_subcontracted = True
            a.department_id = self.subcontractor_id.id


class AddReasonWizard(models.TransientModel):
    _name = 'add.reason.wizard'
    _description = 'Add reason wizard'

    main_id = fields.Many2one('lims.sample.main', 'File number', readonly=True)
    analysis_id = fields.Many2one('lims.analysis', 'analysis', readonly=True)
    sample_id = fields.Many2one('lims.sample.preparation', 'Sample', readonly=True)
    reason_id = fields.Many2one('lims.reason.type', 'Reason')
    domain_reason_type = fields.Char(compute='onchange_reason_domain', store=False, readonly=True)

    @api.depends('main_id', 'analysis_id')
    def onchange_reason_domain(self):
        for rec in self:
            if rec.main_id:
                rec.domain_reason_type = json.dumps([('reason_type', '=', 'file')])
            if rec.analysis_id:
                rec.domain_reason_type = json.dumps([('reason_type', '=', 'analysis')])
            if rec.sample_id:
                rec.domain_reason_type = json.dumps([('reason_type', '=', 'sample')])

    def do_confirm(self):
        res = False
        if self.analysis_id:
            if self.analysis_id.department_id.id in self.env.user.department_ids.ids and self.env.user.has_group(
                    'lims.group_lims_responsible'):
                res = self.analysis_id.sudo().write(
                    {'reason_id': self.reason_id.id, 'state': 'rework', 'date_result': False})
                activity = self.env['mail.activity'].search([
                    ('res_model_id', '=', 'lims.analysis'),
                    ('res_id', '=', self.analysis_id.id),
                    ('user_id', '=', self.analysis_id.user_id.id),
                    ('activity_type_id', '=', self.env.ref('lims.activity_analysis').id)
                ], limit=1)
                if activity:
                    # record._update_activity(activity)
                    activity.action_feedback(feedback=_('Please rework this Analysis %s ') % (self.analysis_id.name))
                    activity = self.analysis_id.activity_schedule(
                        'lims.activity_analysis',
                        summary='Analysis %s has been assigned to you' % self.analysis_id.name,
                        user_id=self.analysis_id.user_id.id
                    )
                result = self.analysis_id.update_result()
                result.reason_id = self.reason_id.id
                # self.analysis_id.is_critical = False
        if self.main_id and self.env.user.has_group('lims.group_lims_responsible'):
            res = self.main_id.do_reject()
            self.main_id.reason_id = self.reason_id.id
            if res and self.reason_id.send_sms:
                templ_reject = self.reason_id.templ_reject.content.replace('{reason}', self.reason_id.name).replace(
                    '{patient}', self.main_id.partner_id.name)
                numbers = str(self.main_id.partner_id.phone) + ',' + (self.main_id.create_uid.mobile_phone)
                logger = self.env.company.send_sms(self.main_id, templ_reject, numbers)
                if logger:
                    logger.main_id = self.main_id.id

        if self.sample_id and self.env.user.has_group('lims.group_lims_responsible'):
            self.sample_id.state = 'cancel'
            self.sample_id.sample_date = False
            if all(s.state == 'cancel' for s in self.sample_id.main_id.sample_line_prepared):
                self.sample_id.main_id.state = 'reject'
            if self.reason_id.send_sms:
                templ_reject = self.reason_id.templ_reject.content.replace('{reason}', self.reason_id.name).replace(
                    '{patient}', self.sample_id.partner_id.name)
                numbers = str(self.sample_id.partner_id.phone) + ',' + (self.sample_id.create_uid.mobile_phone)
                self.env.company.send_sms(self.sample_id, templ_reject, numbers)
        return res


class LimsReasonType(models.Model):
    _name = 'lims.reason.type'
    _description = 'Reasons'

    name = fields.Char('Reason', index=True)
    active = fields.Boolean('Active', default=True)
    reason_type = fields.Selection([('analysis', 'Analysis'), ('file', 'File'), ('sample', 'Sample')])
    send_sms = fields.Boolean("Send Sms")


class LimsResultHistory(models.Model):
    _name = 'lims.result.history'
    _description = 'Result History'

    analysis_id = fields.Many2one('lims.analysis', 'Test')
    name = fields.Char('Parameter')
    user_id = fields.Many2one('res.users', 'Analyst')
    method_id = fields.Many2one('lims.method', 'Method')
    result = fields.Char('Old result')
    reason_id = fields.Many2one('lims.reason.type', 'Reason')