# -*- coding: utf-8 -*-
from odoo import models


class LimsGeotechSite(models.Model):
    _name = 'lims.geotech.site'
    _inherit = ['lims.geotech.site', 'lims.project.bridge.mixin']

    def _project_bridge_record_name(self):
        self.ensure_one()
        return self.site_name or self.name

    def _project_bridge_partner(self):
        self.ensure_one()
        return self.partner_id

    def _project_bridge_sale_order(self):
        self.ensure_one()
        return self.sale_order_id
