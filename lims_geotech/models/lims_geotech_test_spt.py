# -*- coding: utf-8 -*-
from odoo import api, fields, models


class LimsGeotechTestSPT(models.Model):
    _name = 'lims.geotech.test.spt'
    _description = 'Standard Penetration Test (SPT)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'name'

    name = fields.Char('Test No.', default='New', copy=False, index=True, tracking=True)
    borehole_id = fields.Many2one('lims.geotech.borehole', string='Borehole', required=True,
                                  ondelete='cascade', tracking=True)
    analysis_id = fields.Many2one('lims.analysis', string='Analysis',
                                  help='Link to the LIMS test/parameter record driving invoicing and reporting')

    test_date = fields.Datetime('Test Date', default=fields.Datetime.now)
    depth_from = fields.Float('Depth From (m)', required=True)
    depth_to = fields.Float('Depth To (m)', required=True)
    casing_depth = fields.Float('Casing Depth (m)')
    groundwater_depth = fields.Float('Groundwater Depth (m)')
    soil_description = fields.Char('Soil / Sample Description')

    sampler_type = fields.Selection([
        ('split_spoon', 'Split Spoon'),
        ('thin_wall', 'Thin Wall'),
        ('other', 'Other'),
    ], string='Sampler Type', default='split_spoon')

    hammer_weight = fields.Float('Hammer Weight (kg)', default=63.5)
    drop_height = fields.Float('Drop Height (cm)', default=76.0)

    line_ids = fields.One2many('lims.geotech.test.spt.line', 'spt_id', string='Blow Count Intervals')
    n_value = fields.Integer('N-Value', compute='_compute_n_value', store=True,
                             help='Sum of blows for the 2nd and 3rd 150mm intervals (seating drive excluded)')
    refusal = fields.Boolean('Refusal', compute='_compute_n_value', store=True,
                             help='Set when any interval records 50 or more blows')

    technician_id = fields.Many2one('hr.employee', string='Technician', tracking=True)
    validated_by = fields.Many2one('res.users', string='Validated by', readonly=True, copy=False)
    validated_on = fields.Datetime('Validation Date', readonly=True, copy=False)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('in_progress', 'In Progress'),
        ('done', 'Done'),
        ('validated', 'Validated'),
    ], string='Status', default='draft', tracking=True, copy=False)

    active = fields.Boolean('Active', default=True)
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company)

    @api.depends('line_ids.blows', 'line_ids.is_seating')
    def _compute_n_value(self):
        for test in self:
            counted_lines = test.line_ids.filtered(lambda l: not l.is_seating)
            test.n_value = sum(counted_lines.mapped('blows'))
            test.refusal = any(line.blows >= 50 for line in test.line_ids)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('lims.geotech.test.spt') or 'New'
        return super().create(vals_list)

    def action_validate(self):
        self.write({
            'state': 'validated',
            'validated_by': self.env.user.id,
            'validated_on': fields.Datetime.now(),
        })


class LimsGeotechTestSPTLine(models.Model):
    _name = 'lims.geotech.test.spt.line'
    _description = 'SPT Blow Count Interval'
    _order = 'spt_id, sequence'

    spt_id = fields.Many2one('lims.geotech.test.spt', string='SPT Test', required=True, ondelete='cascade')
    sequence = fields.Integer('Interval No.', default=1)
    interval_label = fields.Char('Interval', default='0-15 cm')
    is_seating = fields.Boolean('Seating Drive', help='First 150mm increment, excluded from the N-value')
    blows = fields.Integer('Blow Count', required=True)
    remarks = fields.Char('Remarks')
