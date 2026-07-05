# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api


class ResCompany(models.Model):
    _inherit = 'res.company'

    def _compute_sequence_domain(self):
        """Override to dynamically add 'lims.report' to the domain"""
        updated_domain = []
        for company in self:
            domain = super(ResCompany, self)._compute_sequence_domain()

            # Extract existing 'code' filter from the domain
            lims_codes = []
            for condition in domain:
                if condition[0] == "code" and condition[1] == "in":
                    lims_codes = condition[2]  # Extract list of existing codes
                    break

            # Add 'lims.report' if not already included
            if "lims.batch" not in lims_codes:
                lims_codes.append("lims.batch")

            # Rebuild the domain with the updated list
            updated_domain = [
                ("company_id", "=", company.id),
                ("code", "in", lims_codes)
            ]
        return updated_domain
