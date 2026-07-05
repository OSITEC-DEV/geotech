# -*- coding: utf-8 -*-
from odoo import api, fields, models


class LimsSpecialProjectPermit(models.Model):
    _name = 'lims.special.project.permit'
    _description = 'Special Project QC Permit'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'name desc'

    name = fields.Char('Permit No.', default='New', copy=False, index=True, tracking=True)
    project_id = fields.Many2one('project.project', string='Project', tracking=True)
    partner_id = fields.Many2one('res.partner', string='Customer', tracking=True)
    laboratory_id = fields.Many2one('lims.laboratory', string='Laboratory',
                                    default=lambda self: self.env.user.default_laboratory_id.id)

    date = fields.Datetime('Permit Date', default=fields.Datetime.now, tracking=True)
    work_location = fields.Char('Work Location')
    required_tests = fields.Char('Required Tests / Services')
    equipment_used = fields.Char('Equipment Used')
    environmental_conditions = fields.Char('Environmental Conditions')

    station_ids = fields.One2many('lims.special.project.station', 'permit_id', string='Site Stations')
    station_count = fields.Integer('Station Count', compute='_compute_station_count')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('closed', 'Closed'),
    ], string='Status', default='draft', tracking=True, copy=False)

    approved_by = fields.Many2one('res.users', string='Approved by', readonly=True, copy=False)
    approved_on = fields.Datetime('Approval Date', readonly=True, copy=False)

    active = fields.Boolean('Active', default=True)
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company)
    notes = fields.Text('Notes')

    @api.depends('station_ids')
    def _compute_station_count(self):
        for permit in self:
            permit.station_count = len(permit.station_ids)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('lims.special.project.permit') or 'New'
        return super().create(vals_list)

    def action_submit(self):
        self.write({'state': 'submitted'})

    def action_approve(self):
        self.write({'state': 'approved', 'approved_by': self.env.user.id, 'approved_on': fields.Datetime.now()})

    def action_reject(self):
        self.write({'state': 'rejected'})

    def action_close(self):
        self.write({'state': 'closed'})
