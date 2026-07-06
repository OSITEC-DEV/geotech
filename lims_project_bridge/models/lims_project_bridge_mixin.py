# -*- coding: utf-8 -*-
import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)

# (field name to store the generated task on, task title)
TASK_TEMPLATE = [
    ('task_site_prep_id', 'Site Preparation'),
    ('task_mobilization_id', 'Mobilization'),
    ('task_execution_id', 'Test Execution'),
    ('task_reporting_id', 'Data Entry & Report Drafting'),
]


class LimsProjectBridgeMixin(models.AbstractModel):
    """Shared "generate the standard project + task set" behavior for
    site-level LIMS records (geotech sites, special project permits).

    Inheriting models are expected to already define their own `project_id`
    (lims.geotech.site and lims.special.project.permit both do), and to
    implement the three `_project_bridge_*` methods below.

    Field names on project.task / sale.order used here are checked at
    runtime (via `_fields`) rather than assumed, since this targets a very
    recent Odoo version whose exact Project/Sale internals could not be
    verified against a live instance while this was written.
    """
    _name = 'lims.project.bridge.mixin'
    _description = 'LIMS Project Bridge Mixin'

    task_site_prep_id = fields.Many2one('project.task', string='Site Preparation Task',
                                        readonly=True, copy=False)
    task_mobilization_id = fields.Many2one('project.task', string='Mobilization Task',
                                           readonly=True, copy=False)
    task_execution_id = fields.Many2one('project.task', string='Test Execution Task',
                                        readonly=True, copy=False)
    task_reporting_id = fields.Many2one('project.task', string='Data Entry & Report Task',
                                        readonly=True, copy=False)

    def _project_bridge_record_name(self):
        """Human name used for the auto-created project and task titles."""
        self.ensure_one()
        return self.display_name or self.name

    def _project_bridge_partner(self):
        """res.partner to set on an auto-created project, or an empty recordset."""
        self.ensure_one()
        return self.env['res.partner']

    def _project_bridge_sale_order(self):
        """sale.order this record originates from, or an empty recordset.

        If sale_project already created a project for that order, we reuse
        it instead of creating a second one.
        """
        self.ensure_one()
        return self.env['sale.order']

    def _get_or_create_project(self):
        self.ensure_one()
        if self.project_id:
            return self.project_id

        project = self.env['project.project']
        sale_order = self._project_bridge_sale_order()
        if sale_order:
            if 'project_ids' in sale_order._fields and sale_order.project_ids:
                project = sale_order.project_ids[0]
            elif 'project_id' in sale_order._fields and sale_order.project_id:
                project = sale_order.project_id

        if not project:
            vals = {'name': self._project_bridge_record_name()}
            partner = self._project_bridge_partner()
            if partner and 'partner_id' in self.env['project.project']._fields:
                vals['partner_id'] = partner.id
            project = self.env['project.project'].create(vals)

        self.project_id = project.id
        return project

    def action_generate_project_tasks(self):
        Task = self.env['project.task']
        for rec in self:
            project = rec._get_or_create_project()
            record_name = rec._project_bridge_record_name()
            partner = rec._project_bridge_partner()

            for field_name, task_title in TASK_TEMPLATE:
                if rec[field_name]:
                    continue

                full_name = f"{task_title} - {record_name}"
                existing = Task.search([
                    ('project_id', '=', project.id),
                    ('name', '=', full_name),
                ], limit=1)
                if existing:
                    rec[field_name] = existing.id
                    continue

                vals = {'name': full_name, 'project_id': project.id}
                if partner and 'partner_id' in Task._fields:
                    vals['partner_id'] = partner.id

                try:
                    task = Task.create(vals)
                    rec[field_name] = task.id
                except Exception:
                    _logger.exception(
                        'lims_project_bridge: could not create task %r on project %s',
                        full_name, project.id,
                    )
        return True

    def action_view_project(self):
        self.ensure_one()
        project = self._get_or_create_project()
        return {
            'type': 'ir.actions.act_window',
            'name': project.name,
            'res_model': 'project.project',
            'res_id': project.id,
            'view_mode': 'form',
        }
