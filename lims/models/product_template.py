# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.exceptions import UserError


class ProductTemplate(models.Model):
    _inherit = 'product.template'


    # isSample = fields.Boolean('For Sampling')
    isParameter = fields.Boolean('Parameter/Test')
    department_ids = fields.Many2many('lims.department', string='Departments')
    method_ids = fields.Many2many('lims.method', 'product_method_rel', string='Instruments')
    type_result = fields.Selection([('num', 'Numeric'), ('se', 'selection'), ('txt', 'Text')])
    se_results = fields.Many2many('lims.result', string='Suggested results')
    reference_ids = fields.One2many('lims.result.range', 'product_id', 'Range/Reference')
    isPack = fields.Boolean('Pack/Group of tests')
    parent_pack = fields.Many2many(comodel_name='product.template', relation='parameter_pack_relation',
                                   column1='pack_id', column2='parameter_id', domain=[('isPack', '=', True)])
    child_ids = fields.Many2many(
        comodel_name='product.product',
        relation='pack_product_rel',
        column1='pack_id',
        column2='product_id',
        string='Parameters',
        domain=['|', ('isParameter', '=', True), ('isPack', '=', True)],
    )
    estimated_time = fields.Float(string='Estimated Time (Hours)')
    default_sample_type = fields.Many2one('lims.sample.type', 'Sample Type')
    nb_decimal = fields.Integer(string='Nb decimal', default=2)
    optimum_volume = fields.Float("Optimum volume")
    collection_tube = fields.Many2one('lims.sample.tube', 'Packaging')

    lab_validated = fields.Boolean("Reviewed and validated",tracking=True)
    finance_validated = fields.Boolean("Finance validated",tracking=True)

    @api.model_create_multi
    def create(self, vals):
        missing_fields = ['department_ids', 'type_result', 'estimated_time', 'default_sample_type', 'collection_tube']
        if 'isParameter' in vals and vals['isParameter']:
            for m in missing_fields:
                if not vals[m]:
                    raise UserError('Please add the missing field: ' + str(m))
        result = super(ProductTemplate, self).create(vals)
        return result


class LimsSampleType(models.Model):
    _name = 'lims.sample.type'
    _description = "Sample Type"
    name = fields.Char('Type')
    sample_name = fields.Char('Sample Name')
    uom_id = fields.Many2one('uom.uom', string='Uom')
    split_by_department = fields.Boolean("Split Sample code by department")
    available_on_portal = fields.Boolean("Available on Portal")

    @api.model
    def _name_search(self, name='', domain=None, operator='ilike', limit=100, order=None):
        domain = domain or []
        if name:
            domain = ['|', ('name', operator, name), ('sample_name', operator, name)] + domain
        return self._search(domain, limit=limit, order=order)


class LimsSampleTube(models.Model):
    _name = 'lims.sample.tube'
    _description = "Sample Packaging"
    name = fields.Char('Package')
    active = fields.Boolean('active', default=True)
