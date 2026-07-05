# -*- coding: utf-8 -*-
from odoo import api, fields, models


class LimsSpecialProjectStation(models.Model):
    _name = 'lims.special.project.station'
    _description = 'Special Project Site Station'
    _rec_name = 'name'
    _order = 'name'

    name = fields.Char('Station No.', required=True)
    permit_id = fields.Many2one('lims.special.project.permit', string='Permit', required=True,
                                ondelete='cascade')
    location = fields.Char('Location Description')

    layer_ids = fields.One2many('lims.special.project.layer', 'station_id', string='Layers')
    layer_count = fields.Integer('Layer Count', compute='_compute_layer_count')

    notes = fields.Text('Notes')

    @api.depends('layer_ids')
    def _compute_layer_count(self):
        for station in self:
            station.layer_count = len(station.layer_ids)
