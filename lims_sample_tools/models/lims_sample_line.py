# -*- coding: utf-8 -*-
from odoo import fields, models


class LimsSampleLine(models.Model):
    _inherit = 'lims.sample.line'

    test_units = fields.Json('Units per Test', default=dict,
                             help='product_id -> number of units, set by the test catalogue picker.')
    subcontracting = fields.Json('Subcontracting', default=dict,
                                 help='product_id -> department_id, set by the test catalogue picker.')
