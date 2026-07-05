# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
import math as m
import statistics as s
from odoo.exceptions import ValidationError


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    # isSample = fields.Boolean('For Sampling')
    input_result_ids = fields.Many2many('lims.result.input.type', string='Input results type')
    is_calculated = fields.Boolean("Calculated Result")
    correspondence_ids = fields.One2many('lims.parameter.correspondence', 'product_id', 'Table of correspondence')
    formula = fields.Char("Formula")
    do_generate_inputs = fields.Boolean(help="Generate Inputs after make wip the analysis",default=True)
    def test_formula(self):
        formula = self.formula
        for c in self.correspondence_ids:
            if '[' + c.code + ']' in formula:
                formula = formula.replace('[' + c.code + ']', str(c.test_value))
                formula = formula.replace('[age]', str(30)) if '[age]' in formula else formula
                formula = formula.replace('[weight]', str(72)) if '[weight]' in formula else formula
                patient_info = "age:30 , weight: 72 kg"
            else:
                raise ValidationError('Please check the correspondence code' + str('[' + c.code + ']'))
        result = eval(formula)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': ('Calculation Result'),
                'message': ("Test Customer %s .\nResult = : %s" % (patient_info, str(result))),
                'sticky': False,
            }
        }


class LimsParameterCorrespondence(models.Model):
    _name = 'lims.parameter.correspondence'
    _description = "Parameter Correspondence"

    product_id = fields.Many2one('product.template')
    code = fields.Char('Correspondence code')
    test_value = fields.Float("Test Value")
    parameter_id = fields.Many2one('product.template', domain=[('type_result', '=', 'num')])


class ProductProduct(models.Model):
    _inherit = 'product.product'

    # def test_formula(self):
    #     formula = self.formula
    #     for c in self.correspondence_ids:
    #         if '[' + c.code + ']' in formula:
    #             formula = formula.replace('[' + c.code + ']', str(c.test_value))
    #             formula = formula.replace('[age]', str(30)) if '[age]' in formula else formula
    #             formula = formula.replace('[weight]', str(72)) if '[weight]' in formula else formula
    #             patient_info = "age:30 , weight: 72 kg"
    #         else:
    #             raise ValidationError('Please check the correspondence code' + str('[' + c.code + ']'))
    #     result = eval(formula)
    #     return {
    #         'type': 'ir.actions.client',
    #         'tag': 'display_notification',
    #         'params': {
    #             'title': ('Calculation Result'),
    #             'message': ("Test Customer %s .\nResult = : %s" % (patient_info, str(result))),
    #             'sticky': False,
    #         }
    #     }
