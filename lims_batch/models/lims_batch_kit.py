# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
import math as m
import statistics as s
from odoo.exceptions import UserError, ValidationError
import json


class LimsBatchKit(models.Model):
    _name = 'lims.batch.kit'
    _description = 'Lims Batch Kit'

    name = fields.Char("Kit name")
    department_id = fields.Many2one("lims.department", "Department")
    kit_line = fields.One2many("lims.batch.kit.line", "kit_id", "Batch Kit")
    operators = fields.One2many("lims.batch.kit.operator", "kit_id", string="Operators")
    duration = fields.Float("Duration (Hours)")


class LimsBatchKitOperators(models.Model):
    _name = 'lims.batch.kit.operator'
    _description = 'Lims Batch KIT Operators'

    operator_id = fields.Many2one("hr.employee", "Operator")
    duration = fields.Float("Duration")
    kit_id = fields.Many2one("lims.batch.kit", string="Batch number", required=True)
    company_id = fields.Many2one('res.company', 'Company')


class LimsBatchKitLine(models.Model):
    _name = 'lims.batch.kit.line'
    _description = 'Lims Batch Kit Line'

    @api.depends('quantity', 'product_id')
    def _compute_total_cost(self):
        for line in self:
            line.cost_per_unit = line.product_id.standard_price * line.quantity

    type = fields.Selection([('Reagent', 'Reagent'),
                             ('Consumable', 'Consumable'),
                             ('Labor', 'Labor'),
                             ('Instrument', 'Instrument'),
                             ('utility', 'Utility'),
                             ], string="Type", required=True)

    product_id = fields.Many2one("product.product", string="Product", required=True)
    quantity = fields.Float("Quantity", default=1.0, digits='Batch cost')
    uom_id = fields.Many2one('uom.uom', string='Unit of Measure')
    cost_per_unit = fields.Float("Cost", compute="_compute_total_cost")
    kit_id = fields.Many2one("lims.batch.kit", string="KIT")


