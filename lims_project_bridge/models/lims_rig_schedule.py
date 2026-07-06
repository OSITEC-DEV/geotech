# -*- coding: utf-8 -*-
import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class LimsRigSchedule(models.Model):
    _inherit = 'lims.rig.schedule'

    task_id = fields.Many2one('project.task', string='Project Task',
                              domain="[('project_id', '=', project_id)]",
                              help='Which project task this rig deployment fulfills, '
                                   'e.g. Mobilization or Test Execution.')

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._sync_task_dates()
        return records

    def write(self, vals):
        res = super().write(vals)
        if {'task_id', 'date_start', 'date_end'} & set(vals.keys()):
            self._sync_task_dates()
        return res

    def _sync_task_dates(self):
        """Push this schedule's dates onto its linked task so the Project
        Gantt reflects real rig deployment windows. Field names on
        project.task are checked at runtime rather than assumed - they
        have changed across Odoo versions and could not be verified here.
        """
        for rec in self:
            if not rec.task_id or not rec.date_start or not rec.date_end:
                continue
            task_fields = rec.task_id._fields
            vals = {}
            for candidate in ('planned_date_begin', 'date_start'):
                if candidate in task_fields:
                    vals[candidate] = rec.date_start
                    break
            for candidate in ('date_deadline', 'date_end'):
                if candidate in task_fields:
                    vals[candidate] = rec.date_end
                    break
            if vals:
                try:
                    rec.task_id.write(vals)
                except Exception:
                    _logger.exception(
                        'lims_project_bridge: could not sync dates onto task %s',
                        rec.task_id.id,
                    )
