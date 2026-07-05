# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    qrcode = fields.Binary('QRcode', attachment=True, store=True)
    laboratory_id = fields.Many2one("lims.laboratory", "Laboratory",
                                    default=lambda self: self.env.user.default_laboratory_id.id)

    def action_confirm(self):
        res = super(SaleOrder, self).action_confirm()
        request = self.env['lims.sample.main'].search([('name', '=', self.origin)], limit=1)
        if request:
            # force_confirm=True bypasses the multi-unit popup that lims_food
            # shows in interactive UI flows — the user already confirmed via
            # the quotation so no dialog is needed here.
            result = request.with_context(force_confirm=True).action_confirm()
            # If action_confirm still returns a client action (unexpected),
            # fall back to action_confirm_force if available.
            if isinstance(result, dict) and result.get('type') == 'ir.actions.client':
                if hasattr(request, 'action_confirm_force'):
                    request.action_confirm_force()
        # self._create_invoices().action_post()
        return res