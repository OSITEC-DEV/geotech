# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models , api


class ResCompany(models.Model):
    _inherit = 'res.company'

    logo_gov = fields.Binary(string='logo gov')
    logo_quality = fields.Binary(string='logo Quality')
    logo_iso = fields.Binary(string='logo ISO')
    translation_template = fields.Many2one('lims.translate.titles', string="Translation Template")
    signature_consult = fields.Binary(string="Consultant Signature")
    signature_quality = fields.Binary(string="QA Signature")
    signature_director = fields.Binary(string="Director Signature")
    split_sample_by_department = fields.Boolean('Split samples by department')
    auto_done = fields.Boolean("Mark the result as done after click on save")

    sequence_ids = fields.One2many(
        "ir.sequence", "company_id", string="LIMS Sequences", domain= lambda self: self._compute_sequence_domain()
    )


    def _compute_sequence_domain(self):
        """Dynamically updates the domain for sequence filtering"""
        lims_codes = ["lims.sample.main", "lims.analysis", "lims.sample.preparation"]
        domain = []
        for company in self:
            domain = [
                ("company_id", "=", company.id),
                ("code", "in", lims_codes)
            ]
        return domain # Apply computed domain