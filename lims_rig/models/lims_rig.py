# -*- coding: utf-8 -*-
from odoo import api, fields, models


class LimsRig(models.Model):
    _name = 'lims.rig'
    _description = 'Soil Testing Rig'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'name'

    name = fields.Char('Rig No.', default='New', copy=False, index=True, tracking=True)
    rig_name = fields.Char('Rig Name', required=True, tracking=True)
    rig_type = fields.Selection([
        ('manual', 'Manual'),
        ('hydraulic', 'Hydraulic'),
        ('truck_mounted', 'Truck-Mounted'),
        ('other', 'Other'),
    ], string='Rig Type', required=True, default='hydraulic', tracking=True)
    manufacturer = fields.Char('Manufacturer')
    model = fields.Char('Model')
    drilling_capacity = fields.Char('Drilling Capacity', help='e.g. depth/diameter specifications')
    ownership_status = fields.Selection([
        ('owned', 'Owned'),
        ('leased', 'Leased'),
    ], string='Ownership', default='owned', tracking=True)
    purchase_date = fields.Date('Purchase Date')
    warranty_end_date = fields.Date('Warranty End Date')

    equipment_id = fields.Many2one('maintenance.equipment', string='Maintenance Equipment',
                                   help='Link to Odoo Maintenance for preventive/corrective maintenance tracking')
    vehicle_id = fields.Many2one('fleet.vehicle', string='Support Vehicle',
                                 help='Auxiliary transport asset used to mobilize this rig')

    operator_id = fields.Many2one('hr.employee', string='Default Operator', tracking=True)
    helper_ids = fields.Many2many('hr.employee', 'lims_rig_helper_rel', 'rig_id', 'employee_id', string='Helpers')
    supervisor_id = fields.Many2one('hr.employee', string='Supervisor', tracking=True)

    state = fields.Selection([
        ('available', 'Available'),
        ('scheduled', 'Scheduled'),
        ('deployed', 'Deployed'),
        ('maintenance', 'Under Maintenance'),
        ('breakdown', 'Breakdown'),
    ], string='Status', default='available', tracking=True, copy=False)

    current_location = fields.Char('Current Location', copy=False)
    usage_hours = fields.Float('Total Usage Hours', copy=False)
    total_boreholes = fields.Integer('Total Boreholes Drilled', copy=False)

    maintenance_hours_interval = fields.Float('Preventive Maintenance Interval (Hours)',
                                              help='Auto-generate a maintenance request once usage hours reach this threshold')

    schedule_ids = fields.One2many('lims.rig.schedule', 'rig_id', string='Schedules')
    schedule_count = fields.Integer('Schedule Count', compute='_compute_schedule_count')

    active = fields.Boolean('Active', default=True)
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company)
    notes = fields.Text('Notes')

    @api.depends('schedule_ids')
    def _compute_schedule_count(self):
        for rig in self:
            rig.schedule_count = len(rig.schedule_ids)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('lims.rig') or 'New'
        return super().create(vals_list)

    def action_view_schedules(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Schedules',
            'res_model': 'lims.rig.schedule',
            'view_mode': 'list,form,calendar',
            'domain': [('rig_id', '=', self.id)],
            'context': {'default_rig_id': self.id},
        }

    def action_set_available(self):
        self.write({'state': 'available'})

    def action_set_maintenance(self):
        self.write({'state': 'maintenance'})

    def action_set_breakdown(self):
        self.write({'state': 'breakdown'})
