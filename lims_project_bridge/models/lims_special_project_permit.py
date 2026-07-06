# -*- coding: utf-8 -*-
from odoo import models


class LimsSpecialProjectPermit(models.Model):
    _name = 'lims.special.project.permit'
    _inherit = ['lims.special.project.permit', 'lims.project.bridge.mixin']

    def _project_bridge_record_name(self):
        self.ensure_one()
        return self.work_location or self.name

    def _project_bridge_partner(self):
        self.ensure_one()
        return self.partner_id
