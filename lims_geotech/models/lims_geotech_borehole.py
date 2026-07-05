# -*- coding: utf-8 -*-
from odoo import api, fields, models


class LimsGeotechBorehole(models.Model):
    _name = 'lims.geotech.borehole'
    _description = 'Geotechnical Borehole'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'name'

    name = fields.Char('Borehole No.', default='New', copy=False, index=True, tracking=True)
    site_id = fields.Many2one('lims.geotech.site', string='Site', required=True, tracking=True,
                              ondelete='cascade')
    main_id = fields.Many2one('lims.sample.main', string='Request',
                              help='Link to the LIMS analysis request driving invoicing and reporting')
    partner_id = fields.Many2one('res.partner', string='Customer', related='site_id.partner_id', store=True)
    rig_schedule_id = fields.Many2one('lims.rig.schedule', string='Rig Deployment', tracking=True)

    drilling_method = fields.Selection([
        ('rotary_wash', 'Rotary Wash'),
        ('auger', 'Auger'),
        ('percussion', 'Percussion'),
        ('rc', 'Rotary Core'),
        ('other', 'Other'),
    ], string='Drilling Method', default='rotary_wash', tracking=True)

    date_start = fields.Datetime('Drilling Start')
    date_end = fields.Datetime('Drilling End')

    ground_level_elevation = fields.Float('Ground Level Elevation (m)')
    total_depth = fields.Float('Total Depth (m)')
    groundwater_depth = fields.Float('Groundwater Depth (m)')

    latitude = fields.Float('Latitude', digits=(10, 6))
    longitude = fields.Float('Longitude', digits=(10, 6))

    technician_id = fields.Many2one('hr.employee', string='Technician', tracking=True)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('drilling', 'Drilling'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True, copy=False)

    spt_ids = fields.One2many('lims.geotech.test.spt', 'borehole_id', string='SPT Tests')
    spt_count = fields.Integer('SPT Count', compute='_compute_spt_count')

    active = fields.Boolean('Active', default=True)
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company)
    notes = fields.Text('Notes')

    @api.depends('spt_ids')
    def _compute_spt_count(self):
        for borehole in self:
            borehole.spt_count = len(borehole.spt_ids)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('lims.geotech.borehole') or 'New'
        return super().create(vals_list)

    def action_start_drilling(self):
        self.write({'state': 'drilling', 'date_start': fields.Datetime.now()})

    def action_complete(self):
        self.write({'state': 'completed', 'date_end': fields.Datetime.now()})

    def action_view_spt_tests(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'SPT Tests',
            'res_model': 'lims.geotech.test.spt',
            'view_mode': 'list,form',
            'domain': [('borehole_id', '=', self.id)],
            'context': {'default_borehole_id': self.id},
        }
