# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class MaintenanceEquipment(models.Model):
    _inherit = 'maintenance.equipment'

    used_inlab = fields.Boolean('Is Laboratory Equipment')
    instrument_id = fields.Many2one('lims.method','Lims Instrument')