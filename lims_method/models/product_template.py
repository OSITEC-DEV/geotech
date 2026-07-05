# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    required_method = fields.Boolean('Required Instrument', default=True)
    default_method_id = fields.Many2one('lims.method.technique', 'Default Method')
