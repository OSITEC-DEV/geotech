# -*- coding: utf-8 -*-
from odoo import fields, models


class LimsMethodReferenceWizard(models.TransientModel):
    _name = 'lims.method.reference.wizard'
    _description = 'Edit Method Reference'

    analysis_id = fields.Many2one('lims.analysis', required=True, readonly=True)
    product_name = fields.Char(related='analysis_id.product_id.name', string='Parameter', readonly=True)
    technique_name = fields.Char(related='analysis_id.technique_id.name', string='Technique', readonly=True)
    method_reference = fields.Char('Method Reference')

    def action_save(self):
        self.ensure_one()
        self.analysis_id.sudo().write({'method_reference': self.method_reference})
        return {'type': 'ir.actions.act_window_close'}
