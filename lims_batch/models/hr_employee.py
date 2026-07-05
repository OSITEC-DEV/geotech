# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
import math as m
import statistics as s
from odoo.exceptions import UserError, ValidationError
import json


class HrEmployee(models.Model):
    _inherit = 'hr.employee'


    gross_salary = fields.Float("Latest gross salary")