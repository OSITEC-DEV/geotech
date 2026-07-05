# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import base64
from io import BytesIO

import qrcode
from odoo import fields, models, _, api
from odoo.exceptions import UserError
import json


class LimsDepartment(models.Model):
    _inherit = 'lims.department'

    default_hide_table = fields.Boolean('Hide Table with references')
    subcontracting_note = fields.Boolean('Subcontracting note', help='Print subcontracting note')
    text_in_report = fields.Text('Default Note', help='default note to add in the report')
    auto_validate_report = fields.Boolean("Auto-Validate Report")
