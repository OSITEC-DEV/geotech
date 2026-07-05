# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
import math as m
import statistics as s
from odoo.exceptions import UserError, ValidationError


class LimsAnalysis(models.Model):
    _inherit = 'lims.analysis'

    batch_id = fields.Many2one("lims.batch","Current Batch")

