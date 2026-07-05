# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class LimsRigSchedule(models.Model):
    _name = 'lims.rig.schedule'
    _description = 'Rig Deployment Schedule'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_start desc'

    name = fields.Char('Reference', default='New', copy=False, index=True, tracking=True)
    rig_id = fields.Many2one('lims.rig', string='Rig', required=True, tracking=True)
    project_id = fields.Many2one('project.project', string='Project', tracking=True)
    sale_order_id = fields.Many2one('sale.order', string='Sales Order', tracking=True)
    partner_id = fields.Many2one('res.partner', string='Customer', tracking=True)

    job_location = fields.Char('Job Location', required=True)
    date_start = fields.Datetime('Expected Start', required=True, tracking=True)
    date_end = fields.Datetime('Expected End', required=True, tracking=True)

    crew_size = fields.Integer('Required Crew Size', default=1)
    operator_id = fields.Many2one('hr.employee', string='Operator', tracking=True)
    helper_ids = fields.Many2many('hr.employee', 'lims_rig_schedule_helper_rel', 'schedule_id', 'employee_id',
                                  string='Helpers')

    priority = fields.Selection([
        ('planned', 'Planned'),
        ('normal', 'Normal'),
        ('urgent', 'Urgent'),
    ], string='Priority', default='normal', tracking=True)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('scheduled', 'Scheduled'),
        ('mobilized', 'Mobilized'),
        ('in_progress', 'In Progress'),
        ('demobilized', 'Demobilized'),
        ('done', 'Done'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True, copy=False)

    mobilization_date = fields.Datetime('Mobilization Date')
    demobilization_date = fields.Datetime('Demobilization Date')
    origin_yard = fields.Char('Origin Yard/Location')

    boreholes_completed = fields.Integer('Boreholes Completed')
    depth_achieved = fields.Float('Depth Achieved (m)')
    samples_collected = fields.Integer('Samples Collected')
    downtime_reason = fields.Selection([
        ('none', 'None'),
        ('weather', 'Weather'),
        ('site_issue', 'Site Issue'),
        ('mechanical', 'Mechanical Breakdown'),
        ('other', 'Other'),
    ], string='Downtime Reason', default='none')

    notes = fields.Text('Field Log Notes')
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('lims.rig.schedule') or 'New'
        return super().create(vals_list)

    @api.constrains('rig_id', 'date_start', 'date_end', 'state')
    def _check_no_overlap(self):
        for record in self:
            if record.state in ('cancelled', 'done') or not record.rig_id:
                continue
            if record.date_start and record.date_end and record.date_start > record.date_end:
                raise ValidationError(_('Expected Start must be before Expected End.'))
            overlapping = self.search([
                ('id', '!=', record.id),
                ('rig_id', '=', record.rig_id.id),
                ('state', 'not in', ('cancelled', 'done')),
                ('date_start', '<', record.date_end),
                ('date_end', '>', record.date_start),
            ], limit=1)
            if overlapping:
                raise ValidationError(_(
                    'Rig "%(rig)s" is already booked on schedule "%(other)s" during this period.',
                    rig=record.rig_id.display_name, other=overlapping.name,
                ))

    def action_mobilize(self):
        self.write({'state': 'mobilized', 'mobilization_date': fields.Datetime.now()})
        self.rig_id.write({'state': 'deployed'})

    def action_start(self):
        self.write({'state': 'in_progress'})

    def action_demobilize(self):
        self.write({'state': 'demobilized', 'demobilization_date': fields.Datetime.now()})

    def action_done(self):
        self.write({'state': 'done'})
        for record in self:
            record.rig_id.write({'state': 'available'})

    def action_cancel(self):
        self.write({'state': 'cancelled'})
