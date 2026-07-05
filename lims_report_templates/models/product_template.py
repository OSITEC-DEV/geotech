# -*- coding: utf-8 -*-

from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    default_template = fields.Many2one('lims.analysis.report', 'Default Template')
    disclaimer = fields.Text('Disclaimer')
    limitations = fields.Text('Limitations')