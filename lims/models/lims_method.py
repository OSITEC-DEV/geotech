# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class LimsMethods(models.Model):
    _name = 'lims.method'
    _description = "Instruments (used before as : Method Model)"

    name = fields.Char('Instrument')
    reference_ids = fields.One2many('lims.result.range', 'method_id', 'Range/Reference')
    active = fields.Boolean('Active', default=True)
    default_uom = fields.Many2one('uom.uom', 'Uom')
    is_default = fields.Boolean('Use by default')
