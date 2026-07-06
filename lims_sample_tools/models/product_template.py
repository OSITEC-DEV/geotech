# -*- coding: utf-8 -*-
from odoo import models, fields


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    allowed_sample_type_ids = fields.Many2many(
        'lims.sample.type', string='Available on Sample Types',
        help='Restricts which samples this test/pack can be selected for in the '
             'test catalogue picker. Leave empty to allow it for every sample type.'
    )
    is_subcontract = fields.Boolean('Subcontract', default=False)


class ProductProduct(models.Model):
    _inherit = 'product.product'

    allowed_sample_type_ids = fields.Many2many(
        related='product_tmpl_id.allowed_sample_type_ids', readonly=False
    )
    is_subcontract = fields.Boolean(related='product_tmpl_id.is_subcontract', readonly=False)
