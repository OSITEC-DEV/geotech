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

    def get_report_limit_data(self):
        """Return all data the ReportSpecWidget dialog needs for one analysis."""
        self.ensure_one()
        limit = self.limit_id

        # All limits available for this analyte (same product)
        available = self.env['lims.analysis.limit'].search([
            ('product_id', '=', self.product_id.id),
            ('active', '=', True),
        ])
        uoms = self.env['uom.uom'].search([], order='name')
        regulations = self.env['lims.rang.factor'].search([], order='name')

        def _limit_dict(l):
            return {
                'id':            l.id,
                'name':          l.name or str(l.id),
                'limit_type':    l.limit_type or 'mrl',
                'mrl':           l.mrl or 0,
                'min_value':     l.min_value or 0,
                'max_value':     l.max_value or 0,
                'lod':           l.lod or 0,
                'loq':           l.loq or 0,
                'regulation_id': l.regulation_id.id if l.regulation_id else False,
                'regulation_name': l.regulation_id.name if l.regulation_id else '',
                'uom_id':        l.uom_id.id if l.uom_id else False,
                'uom_name':      l.uom_id.name if l.uom_id else '',
            }

        # Instrument, sample category and sample type from the analysis context
        sample_line     = getattr(self, 'sample_line_id', False)
        sample_category = sample_line.sample_category_id if sample_line else False
        sample_type     = sample_line.sample if sample_line else False
        instrument      = self.method_id if self.method_id else False

        return {
            'analysis_id':          self.id,
            'analyte_name':         self.product_id.name or '',
            'specification':        self.specification or '',
            'current_limit':        _limit_dict(limit) if limit else None,
            'available_limits':     [_limit_dict(l) for l in available],
            'uoms':                 [{'id': u.id, 'name': u.name} for u in uoms],
            'regulations':          [{'id': r.id, 'name': r.name} for r in regulations],
            # auto-fill context for "Create" tab
            'instrument_name':      instrument.name if instrument else '',
            'sample_category_name': sample_category.name if sample_category else '',
            'sample_type_name':     sample_type.name if sample_type else '',
        }

    def save_report_limit(self, vals):
        """Save limit changes from the ReportSpecWidget dialog.

        vals keys:
          mode            — 'switch' | 'edit' | 'create'
          limit_id        — for 'switch' mode
          limit_type, mrl, min_value, max_value, lod, loq,
          regulation_id, uom_id  — for 'edit' / 'create'
          specification_override  — optional manual spec text
        """
        self.ensure_one()
        mode = vals.get('mode', 'edit')

        if mode == 'switch':
            lid = vals.get('limit_id')
            if lid:
                self.write({'limit_id': int(lid)})
                if hasattr(self, '_refresh_specification'):
                    self._refresh_specification()

        elif mode == 'edit':
            limit = self.limit_id
            if limit:
                clean = {}
                for f in ('mrl', 'min_value', 'max_value'):
                    if f in vals:
                        clean[f] = float(vals[f])
                if vals.get('limit_type') in ('mrl', 'max', 'range'):
                    clean['limit_type'] = vals['limit_type']
                if vals.get('regulation_id'):
                    clean['regulation_id'] = int(vals['regulation_id'])
                else:
                    clean['regulation_id'] = False
                if vals.get('uom_id'):
                    clean['uom_id'] = int(vals['uom_id'])
                if clean:
                    limit.write(clean)
                self.write({'limit_id': limit.id})
                if hasattr(self, '_refresh_specification'):
                    self._refresh_specification()

        elif mode == 'create':
            clean = {
                'product_id': self.product_id.id,
                'limit_type': vals.get('limit_type', 'mrl'),
            }
            if self.method_id:
                clean['instrument_id'] = self.method_id.id
            # Auto-fill sample category and sample type from the analysis's sample line
            sample_line = getattr(self, 'sample_line_id', False)
            if sample_line and sample_line.sample_category_id:
                clean['sample_category_id'] = sample_line.sample_category_id.id
            if sample_line and sample_line.sample:
                clean['sample_type'] = sample_line.sample.id
            for f in ('mrl', 'min_value', 'max_value'):
                if f in vals:
                    clean[f] = float(vals[f])
            if vals.get('regulation_id'):
                clean['regulation_id'] = int(vals['regulation_id'])
            if vals.get('uom_id'):
                clean['uom_id'] = int(vals['uom_id'])
            # Auto-fill LOD/LOQ from technique (via analysis computed fields)
            clean['loq'] = getattr(self, 'loq', 0.0) or 0.0
            clean['lod'] = getattr(self, 'lod', 0.0) or 0.0
            new_limit = self.env['lims.analysis.limit'].create(clean)
            self.write({'limit_id': new_limit.id})
            if hasattr(self, '_refresh_specification'):
                self._refresh_specification()

        # Manual override always wins if provided
        spec_override = vals.get('specification_override', '')
        if spec_override:
            self.write({'specification': spec_override})

        return {
            'specification': self.specification or '',
            'limit_id':   self.limit_id.id if self.limit_id else False,
            'limit_name': self.limit_id.name or '' if self.limit_id else '',
        }

    def action_fix_specification(self):
        """Kept for backward compat — new UI uses ReportSpecWidget OWL dialog."""
        self.ensure_one()
        return {
            'name': _('Fix Limit & Specification'),
            'type': 'ir.actions.act_window',
            'res_model': 'lims.report.spec.fix.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_analysis_id':   self.id,
                'default_limit_id':      self.limit_id.id if self.limit_id else False,
                'default_specification': self.specification or '',
            },
        }

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
