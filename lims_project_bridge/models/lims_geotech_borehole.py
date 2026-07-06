# -*- coding: utf-8 -*-
from odoo import api, fields, models


class LimsGeotechBorehole(models.Model):
    _inherit = 'lims.geotech.borehole'

    task_id = fields.Many2one('project.task', string='Project Task',
                              domain="[('project_id', '=', site_project_id)]",
                              help='Which project task tracks the drilling/testing of this borehole.')
    site_project_id = fields.Many2one(related='site_id.project_id', string='Site Project', store=False)

    @api.onchange('site_id')
    def _onchange_site_default_task(self):
        if self.site_id and self.site_id.task_execution_id and not self.task_id:
            self.task_id = self.site_id.task_execution_id
