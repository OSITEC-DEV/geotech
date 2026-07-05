# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    department_ids = fields.Many2many('lims.department', string='Departments')
    signature_image = fields.Binary("E-signature", attachment=True)
    default_laboratory_id = fields.Many2one("lims.laboratory", "Default Laboratory")

    def get_job_id(self):
        for record in self:
            employee = record.env['hr.employee'].search_read([('user_id', '=', record.id)], ['job_id'], limit=0)
            if employee and employee[0]['job_id']:
                return employee[0]['job_id'][1]
            else:
                return ""
