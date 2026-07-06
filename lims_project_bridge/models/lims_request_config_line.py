# -*- coding: utf-8 -*-
from odoo import fields, models


class LimsRequestConfigLine(models.Model):
    _inherit = 'lims.request.config.line'

    analytic_distribution = fields.Json(
        'Analytic Distribution',
        help='Set manually to roll this line\'s cost up onto a project (or any other) '
             'analytic account. Not auto-filled - lims.sample.main has no reliable, '
             'generic link to a single project to default it from.'
    )
