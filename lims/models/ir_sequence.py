# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class IrSequence(models.Model):
    _inherit = 'ir.sequence'

    laboratory_id = fields.Many2one("lims.laboratory","Laboratory",default=lambda self: self.env.user.default_laboratory_id.id)