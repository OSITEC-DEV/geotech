# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api
from odoo.exceptions import ValidationError


class LimsLaboratory(models.Model):
    _name = "lims.laboratory"
    _description = "Laboratory"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _rec_name = "name"
    _order = "name"

    name = fields.Char(
        string="Laboratory Name",
        required=True,
        tracking=True,
    )

    code = fields.Char(
        string="Code",
        required=True,
        tracking=True
    )

    active = fields.Boolean(
        string="Active",
        default=True
    )

    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company
    )

    partner_id = fields.Many2one(
        "res.partner",
        string="Partner / Address"
    )

    manager_id = fields.Many2one(
        "res.users",
        string="Laboratory Manager"
    )

    user_ids = fields.Many2many(
        "res.users",
        "lims_laboratory_user_rel",
        "laboratory_id",
        "user_id",
        string="Authorized Users"
    )

    department_ids = fields.One2many(
        "lims.department",
        "laboratory_id",
        string="Departments"
    )

    sequence_ids = fields.One2many(
        "ir.sequence",
        "laboratory_id",
        string="Sequences"
    )

    notes = fields.Text(
        string="Notes"
    )

    department_count = fields.Integer(
        compute="_compute_counts",
        string="# Departments"
    )

    sequence_count = fields.Integer(
        compute="_compute_counts",
        string="# Sequences"
    )

    @api.depends("department_ids", "sequence_ids")
    def _compute_counts(self):
        for rec in self:
            rec.department_count = len(rec.department_ids)
            rec.sequence_count = len(rec.sequence_ids)

    _sql_constraints = [
        ('lims_laboratory_code_unique',
         'unique(code, company_id)',
         'Laboratory code must be unique per company!')
    ]

    
    def action_open_departments(self):
        self.ensure_one()
    
        return {
            'name': 'Departments',
            'type': 'ir.actions.act_window',
            'res_model': 'lims.department',
            'view_mode': 'list,form',
            'domain': [('laboratory_id', '=', self.id)],
            'context': {
                'default_laboratory_id': self.id
            },
        }

    def action_open_sequences(self):
        self.ensure_one()
    
        return {
            "name": "Sequences",
            "type": "ir.actions.act_window",
            "res_model": "ir.sequence",
            "view_mode": "list,form",
            "domain": [("laboratory_id", "=", self.id)],
            "context": {
                "default_laboratory_id": self.id
            },
        }