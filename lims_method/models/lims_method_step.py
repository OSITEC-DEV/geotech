# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class LimsMethodStep(models.Model):
    _name = 'lims.method.step'
    _description = "Steps of method"

    name = fields.Char('Title')
    sequence = fields.Integer('Sequence')
    timeline = fields.Float('Timming')
    attachment = fields.Binary('Attachment Reference')
    version = fields.Integer('Version', readonly=True)
    state = fields.Selection([('draft', 'Draft'), ('validated', 'Validated')], default='draft')
    user_id = fields.Many2one('res.users', 'Assigned To', default=lambda self: self.env.user)
    need_approve = fields.Boolean('Require validation', help='This step must be validated to move on to the next step.')
    default_equipment_id = fields.Many2one('maintenance.equipment', 'Equipment', domain=[('used_inlab', '=', True)])

    def do_validate(self):
        self.state = 'validated'
        self.version += 1

    def reset_draft(self):
        self.state = 'draft'
