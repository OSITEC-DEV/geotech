# -*- coding: utf-8 -*-
from odoo import fields, models


class LimsSampleMain(models.Model):
    _inherit = 'lims.sample.main'

    request_category = fields.Selection([
        ('private', 'Private'),
        ('government', 'Government'),
        ('project', 'Project'),
    ], string='Request Category', default='private', tracking=True)

    config_line_ids = fields.One2many('lims.request.config.line', 'main_id', string='Configuration Lines')

    def action_open_sample_wizard(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Edit Samples',
            'res_model': 'lims.sample.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_main_id': self.id,
                'default_sample_ids': [(6, 0, self.sample_line_prepared.ids)],
            },
        }
