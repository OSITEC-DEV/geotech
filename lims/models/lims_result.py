# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class LimsResult(models.Model):
    _name = 'lims.result'
    _description = "Lims Result Type"
    name = fields.Char('Result type',translate=True)
    active = fields.Boolean('Active', default=True)
    state = fields.Many2one('lims.result.state')
    code = fields.Char("Code")

class LimsResult(models.Model):
    _name = 'lims.result.state'
    _description = "Lims result status"

    name = fields.Char('State')
    color = fields.Char('Color', help='Please enter here your code rbg color !')
    code = fields.Char('Code')


class LimsResultRange(models.Model):
    _name = 'lims.result.range'
    _description = "Lims references and ranges"

    def get_optimum_state(self):
        optimum_state = self.env['lims.result.state'].search([('code', '=', 'OK')], limit=1)
        if len(optimum_state):
            return optimum_state.id
        else:
            raise UserError(_('Optimum state does not exist, please add this state first'))

    type_range = fields.Selection([('numeric', 'Numerical'), ('txt', 'Text')], default='numeric')
    factor_id = fields.Many2one('lims.rang.factor', 'Factor',
                                default=lambda self: self.env.ref('lims.default_rang_factor', False))
    min_val = fields.Float('Min value', digits=(16, 4))
    max_val = fields.Float('Max value', digits=(16, 4))
    text_rang = fields.Text("range....")
    status = fields.Many2one('lims.result.state', 'state', default=get_optimum_state)
    product_id = fields.Many2one('product.template', 'Parameter',
                                 domain=[('type', '=', 'service'), ('isParameter', '=', True)])
    method_id = fields.Many2one('lims.method', 'Method')
    uom_id = fields.Many2one('uom.uom', default=lambda self: self.product_id.uom_id.id)

    @api.onchange('min_val', 'max_val')
    def onchange_rang(self):
        if self.min_val and self.max_val:
            self.text_rang = str(self.min_val) + " - " + str(self.max_val)


class LimsRangFactor(models.Model):
    _name = 'lims.rang.factor'
    _description = 'Factors of rang'

    name = fields.Char("Title")
    description = fields.Text("Description of Factor")

