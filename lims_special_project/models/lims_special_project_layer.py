# -*- coding: utf-8 -*-
from odoo import fields, models


class LimsSpecialProjectLayer(models.Model):
    _name = 'lims.special.project.layer'
    _description = 'Special Project Layer'
    _rec_name = 'name'
    _order = 'station_id, sequence'

    name = fields.Char('Layer No.', required=True)
    sequence = fields.Integer('Sequence', default=1)
    station_id = fields.Many2one('lims.special.project.station', string='Station', required=True,
                                 ondelete='cascade')
    depth_from = fields.Float('Depth From (m)')
    depth_to = fields.Float('Depth To (m)')
    material_description = fields.Char('Material Description')
    analysis_id = fields.Many2one('lims.analysis', string='Analysis',
                                  help='Link to the LIMS test/parameter record performed on this layer')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('tested', 'Tested'),
        ('approved', 'Approved'),
    ], string='Status', default='draft')
