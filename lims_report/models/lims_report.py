# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import base64
from io import BytesIO

import qrcode
from odoo import fields, models, _, api
from odoo.exceptions import UserError
import json


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    @api.model_create_multi
    def create(self, vals):
        if 'res_model' in vals and vals['res_model'] == 'lims.report':
            vals['public'] = True
        result = super(IrAttachment, self).create(vals)
        return result


class LimsReport(models.Model):
    _name = 'lims.report'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'sequence.mixin', 'utm.mixin']
    _description = "Medical Analysis Report"
    _rec_name = 'name'
    _order = 'date desc'
    sample_lines_display = fields.Char(
        string="Samples",
        compute="_compute_sample_lines_display",
        store=True,
    )

    @api.depends('analysis_ids.sample_line_id')
    def _compute_sample_lines_display(self):
        for rec in self:
            sample_lines = rec.analysis_ids.mapped('sample_line_id')
            sample_lines = sample_lines.sorted(key=lambda r: r.id)
            rec.sample_lines_display = ", ".join(sample_lines.mapped('display_name')) if sample_lines else ""

    def _get_default_template(self):
        return self.env.company.translation_template.id

    name = fields.Char('Report Number')
    date = fields.Datetime('Date report')
    partner_id = fields.Many2one('res.partner', 'Customer', readonly=True)
    company_id = fields.Many2one('res.company', 'Company', related='main_id.company_id')
    user_id = fields.Many2one('res.users', 'Salesperson', readonly=True)
    date_result = fields.Datetime('Date result', readonly=True)
    result = fields.Char('Result', readonly=True)
    main_id = fields.Many2one('lims.sample.main', 'Request', readonly=True)
    product_id = fields.Many2one('product.product', 'Parameter/Pack', readonly=True)
    analysis_ids = fields.One2many('lims.analysis', 'report_id', 'Analysis #', readonly=True)
    qrcode = fields.Binary('QRcode', attachment=True, store=True)
    signature_consult = fields.Binary("Consultant Signature", copy=False)
    signature_quality = fields.Binary("QA Signature", copy=False)
    signature_director = fields.Binary("Director Signature", copy=False)
    translation_template = fields.Many2one('lims.translate.titles', default=_get_default_template)
    state = fields.Selection([('cancel', 'Canceled'), ('ready', 'To review'), ('valid', 'Validated')], default='ready',
                             tracking=True)
    notes = fields.Text('Notes', copy=False)
    print_department = fields.Boolean("Print Department")
    print_method = fields.Boolean("Print Method", default=True)
    print_group_id = fields.Many2one('lims.parameter.print.group', 'Print Group')
    consultant_id = fields.Many2one('res.users', 'Consultant', tracking=True)
    consultant_note = fields.Text('Consultant / Recommendations')
    consultation_date = fields.Datetime('Consultation date', tracking=True, readonly=True, copy=False)
    title = fields.Char("Title")
    hide_table_result = fields.Boolean("Hide result table")
    print_old_result = fields.Boolean("Print previous result")
    print_note = fields.Boolean('Print note', help='Print note')
    version = fields.Integer("Version", copy=False, readonly=True, default=1)
    rawdata_url = fields.Char("raw-data URL")

    def get_attachment_url(self):
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        attachment = self.env["ir.attachment"].sudo().search([('res_id','=',self.id)]).filtered(lambda r: 'backup' not in r.name)
        if attachment:
            url = base_url + ("/web/content/%s?download=true" % attachment[0].id)
            return url

    def sign_consultation(self):
        for record in self:
            if record.env.user.has_group('lims.group_lims_consultant'):
                record.consultant_id = record.env.user.id
                record.consultation_date = fields.datetime.now()
                record.signature_consult = record.env.user.signature_image
            else:
                raise UserError("Oops, You are not allowed to sign as consultant")

    def do_validate(self):
        for record in self:
            if record.env.user.has_group('lims.group_lims_reporting'):
                record.state = 'valid'
                record.generate_qr_code()
                record.date = fields.datetime.now()
                seq_date = fields.Datetime.now()
                record.name = record.env['ir.sequence'].next_by_code('lims.report',
                                                                     sequence_date=seq_date) or _('New')
                record.main_id.state = 'tosend'
            else:
                raise UserError("Ay ya yay...!, Permission denied \n Please contact your administrator")

    def do_cancel(self):
        for record in self:
            request_id = record.main_id
            record.write({
                'state': 'cancel',
                'date': False,
                'signature_consult': False,
                'consultation_date': False,
                'consultant_id': False
            })
            request_id.state = 'tosend'
            request_id.sale_id.report_done = False

    def do_ready(self):
        for record in self:
            record.state = 'ready'
            record.date = fields.datetime.now()

    def preview_analysis_report(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'target': 'new',
            'url': self.get_portal_url() + "&report_type=pdf",
        }

    def _get_report_base_filename(self):
        self.ensure_one()
        return '%s %s' % (self.name, self.partner_id.name)

    def _get_portal_return_action(self):
        """ Return the action used to display orders when returning from customer portal. """
        self.ensure_one()
        return self.env.ref('lims_report.reports_action')

    def unlink(self):
        for order in self:
            if order.state not in ('ready', 'cancel'):
                raise UserError(_('You can not delete a validated report. You must cancel it first.'))
        return super(LimsReport, self).unlink()

    def generate_qr_code(self):
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
            record.qrcode = qr_image
            return qr_image

    def write(self, vals):
        consultant_note = vals.get('consultant_note', False)
        if consultant_note and consultant_note != '<p><br></p>' and not self.env.user.has_group(
                'lims.group_lims_consultant'):
            raise UserError("Permission denied , you are not allowed to write on Consultation note")
        return super(LimsReport, self).write(vals)

    def _compute_access_url(self):
        super(LimsReport, self)._compute_access_url()
        for report in self:
            report.access_url = '/my/reports/%s' % (report.id)

    def reset_report(self):
        return {
            'name': _('Reason of resetting the report'),
            'type': 'ir.actions.act_window',
            'res_model': 'add.reason.wizard',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_report_id': self.id,
                        'default_reason_type': 'report'
                        }
        }


class AddReasonWizard(models.TransientModel):
    _inherit = 'add.reason.wizard'

    report_id = fields.Many2one('lims.report', 'Report')

    @api.depends('main_id', 'analysis_id', 'report_id')
    def onchange_reason_domain(self):
        result = super(AddReasonWizard, self).onchange_reason_domain()
        for rec in self:
            if rec.report_id:
                rec.domain_reason_type = json.dumps([('reason_type', '=', 'report')])
        return result

    def do_confirm(self):
        result = super(AddReasonWizard, self).do_confirm()
        for record in self:
            if record.report_id:
                report = record.report_id
                if report.title:
                    report.title += ' (' + record.reason_id.name + ') '
                else:
                    record.reason_id.name
                record.report_id.state = 'ready'
                report.consultant_id = False
                report.consultation_date = False
                report_id = record.env.ref('lims_report_templates.lims_portal_report_pdf'). \
                    _render_qweb_pdf(res_ids=record.report_id.ids)
                data_record = base64.b64encode(report_id[0])
                version = record.report_id.version
                ir_values = {
                    'name': "Report Backup %s" % record.report_id.version,
                    'type': 'binary',
                    'res_id': record.report_id.id,
                    'res_model': 'lims.report',
                    'datas': data_record,
                    'store_fname': data_record,
                    'mimetype': 'application/x-pdf',
                }
                data_id = record.env['ir.attachment'].create(ir_values)
                record.report_id.version += 1
                record.report_id.message_post(body="Report has been updated to version = %s" % str(version + 1))


class LimsReasonType(models.Model):
    _inherit = 'lims.reason.type'

    reason_type = fields.Selection(selection_add=[('report', 'Report')])


class lims_report_keys(models.Model):
    _name = 'lims.report.keys'
    _description = "Dict of Keys for dynamic reports"

    name = fields.Char("Name")
    model_id = fields.Many2one('ir.model', 'Model')
    dict_key_ids = fields.One2many('lims.report.keys.lines', 'dict_id', "Keys")
    dict_json_ids = fields.One2many('lims.report.keys.json', 'dict_id', "Json Keys")


class lims_report_keys_lines(models.Model):
    _name = 'lims.report.keys.json'
    _description = "Keys for Json reports"

    name = fields.Char("Description")
    key = fields.Char("Key")
    dict_id = fields.Many2one('lims.report.keys', string="Dictionary")


class lims_report_keys_lines(models.Model):
    _name = 'lims.report.keys.lines'
    _description = "Keys for dynamic reports"

    @api.depends('dict_id')
    def onchange_method_domain(self):
        for rec in self:
            dict = rec.dict_id
            rec.domain_model = json.dumps([('model_id', '=', dict.model_id.id)]) if dict.model_id else "[]"

    dict_id = fields.Many2one('lims.report.keys', string="Dictionary")
    key = fields.Char("Key")
    field_id = fields.Many2one('ir.model.fields')
    field_child = fields.Char("Field child", help="Technical name of field child")
    domain_model = fields.Char(compute='onchange_method_domain')


class LimsParameterPrint(models.Model):
    _name = 'lims.parameter.print'
    _description = "Parameter Print"

    name = fields.Char("Name", required=True)
    print_name = fields.Char("Print name")
    print_group_id = fields.Many2one('lims.parameter.print.group', 'Print Group', required=True)
    sequence = fields.Integer("Sequence")


class LimsParameterPrintGroup(models.Model):
    _name = 'lims.parameter.print.group'
    _description = "Parameter Print"

    name = fields.Char("Group Name")
    parameter_print_ids = fields.One2many("lims.parameter.print", 'print_group_id', "Parameters")
    parent_id = fields.Many2one('lims.parameter.print.group', 'Parent group')
    template_id = fields.Many2one('ir.actions.report', string="Report Template")


class ProductTemplate(models.Model):
    _inherit = 'product.template'
    parameter_print_id = fields.Many2one('lims.parameter.print', 'Parameter Print')
