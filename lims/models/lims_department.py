# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class LimsDepartment(models.Model):
    _name = 'lims.department'
    _description = "Laboratory department"

    name = fields.Char('Department')
    manager_id = fields.Many2one('res.users', 'Manager')
    is_subcontractor = fields.Boolean('Subcontractor')
    active = fields.Boolean('Active', default=True)
    partner_id = fields.Many2one('res.partner', string='Partner')
    prefix_code = fields.Char('Prefix code')
    laboratory_id = fields.Many2one("lims.laboratory","Laboratory",default=lambda self: self.env.user.default_laboratory_id.id)