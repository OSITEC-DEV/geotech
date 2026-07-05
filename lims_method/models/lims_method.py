# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class LimsMethod(models.Model):
    _inherit = 'lims.method'

    equipment_id = fields.Many2one('maintenance.equipment', "Equipment", domain=[('used_inlab', '=', True)])
    method_technique_ids = fields.Many2many('lims.method.technique', 'method_technique_rel', 'method_id',
                                            'technique_id', 'Methods')


class LimsMethodTechnique(models.Model):
    _name = 'lims.method.technique'
    _description = 'Technique of method'

    name = fields.Char('Technical name', index=True)
    code = fields.Char('Code')
    active = fields.Boolean("Active", default=True)
    instrument_id = fields.Many2one(
        'lims.method', string="Default Instrument",
        help="The method/instrument this technique is typically performed on."
    )
    sop_documentation = fields.Binary("SOP documentation")
    method_step_ids = fields.Many2many('lims.method.step', 'method_step_rel', 'method_id', 'step_id', 'Default Steps')
    description = fields.Text("Description")

    # Detection limits — LOQ is set manually; LOD is auto-computed as LOQ / 3
    loq = fields.Float(
        'LOQ', digits=(12, 4), store=True,
        help="Limit of Quantification (stored on the technique)"
    )
    lod = fields.Float(
        'LOD', compute='_compute_lod', store=True, digits=(12, 4),
        help="Limit of Detection — automatically set to LOQ / 3"
    )

    @api.depends('loq')
    def _compute_lod(self):
        for rec in self:
            rec.lod = (rec.loq / 3.0) if rec.loq else 0.0

    # Inverse of product.product.default_method_id — gives visibility over
    # which parameter variants use this technique as their default method.
    variant_ids = fields.One2many(
        'product.product', 'default_method_id',
        string='Linked Variants', readonly=True,
    )