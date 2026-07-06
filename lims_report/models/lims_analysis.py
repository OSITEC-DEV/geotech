# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class LimsAnalysis(models.Model):
    _inherit = 'lims.analysis'

    report_id = fields.Many2one('lims.report', 'Report')
    parameter_print_id = fields.Many2one("lims.parameter.print", "Parameter print")
    method_reference = fields.Char(
        'Method Reference',
        help="Analytical method reference shown in the final report. "
             "Auto-filled from the technique when technique changes; "
             "the reporter can override it freely."
    )

    @api.onchange("product_id")
    def onchange_product_parameter(self):
        for record in self:
            if record.product_id:
                record.parameter_print_id = record.product_id.parameter_print_id.id

    @api.onchange('technique_id')
    def _onchange_technique_method_reference(self):
        for rec in self:
            if rec.technique_id:
                rec.method_reference = rec.technique_id.name

    def write(self, vals):
        # Auto-fill method_reference when technique_id is set and reference is blank
        if 'technique_id' in vals and 'method_reference' not in vals:
            for rec in self:
                if not rec.method_reference:
                    technique = self.env['lims.method.technique'].browse(vals['technique_id'])
                    if technique.exists():
                        vals = dict(vals, method_reference=technique.name)
        result = super(LimsAnalysis, self).write(vals)
        if self.report_id.state == 'sent' or self.report_id.consultant_id and self.report_id.state == 'valid':
            raise UserError("This analysis is locked, create the amended or corrective report first")
        return result

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if 'company_id' in vals:
                self = self.with_company(vals['company_id'])
            if vals.get('technique_id') and not vals.get('method_reference'):
                technique = self.env['lims.method.technique'].browse(vals['technique_id'])
                if technique.exists():
                    vals['method_reference'] = technique.name
        result = super(LimsAnalysis, self).create(vals_list)
        for rec in result:
            parameter_print = rec.product_id.parameter_print_id
            if parameter_print:
                rec['parameter_print_id'] = parameter_print.id
        return result

    def create_report_from_analysis(self):
        return {
            'name': _('Report Creation'),
            'type': 'ir.actions.act_window',
            'res_model': 'lims.report.wizard',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_analysis_ids': self.ids}
        }

    def action_edit_method_reference(self):
        """Open a small dialog to edit method_reference without navigating to the analysis form."""
        self.ensure_one()
        return {
            'name': _('Edit Method Reference'),
            'type': 'ir.actions.act_window',
            'res_model': 'lims.method.reference.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_analysis_id': self.id,
                'default_method_reference': self.method_reference or '',
            },
        }
