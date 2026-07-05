# -*- coding: utf-8 -*-
from odoo import api, fields, models


class LimsGeotechSite(models.Model):
    _name = 'lims.geotech.site'
    _description = 'Geotechnical Investigation Site'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'site_name'
    _order = 'name desc'

    name = fields.Char('Reference', default='New', copy=False, index=True, tracking=True)
    site_name = fields.Char('Site Name', required=True, tracking=True)
    partner_id = fields.Many2one('res.partner', string='Customer', tracking=True)
    project_id = fields.Many2one('project.project', string='Project', tracking=True)
    sale_order_id = fields.Many2one('sale.order', string='Sales Order', tracking=True)
    laboratory_id = fields.Many2one('lims.laboratory', string='Laboratory',
                                    default=lambda self: self.env.user.default_laboratory_id.id)

    location = fields.Char('Address / Location Description')
    latitude = fields.Float('Latitude', digits=(10, 6))
    longitude = fields.Float('Longitude', digits=(10, 6))

    date_start = fields.Date('Investigation Start')
    date_end = fields.Date('Investigation End')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('closed', 'Closed'),
    ], string='Status', default='draft', tracking=True, copy=False)

    borehole_ids = fields.One2many('lims.geotech.borehole', 'site_id', string='Boreholes')
    borehole_count = fields.Integer('Borehole Count', compute='_compute_borehole_count')

    active = fields.Boolean('Active', default=True)
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company)
    notes = fields.Text('Notes')

    @api.depends('borehole_ids')
    def _compute_borehole_count(self):
        for site in self:
            site.borehole_count = len(site.borehole_ids)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('lims.geotech.site') or 'New'
        return super().create(vals_list)

    def action_view_boreholes(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Boreholes',
            'res_model': 'lims.geotech.borehole',
            'view_mode': 'list,form',
            'domain': [('site_id', '=', self.id)],
            'context': {'default_site_id': self.id},
        }
