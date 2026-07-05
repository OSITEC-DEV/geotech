# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    analysis_ids = fields.One2many('lims.analysis', 'partner_id', 'Analysis')

    def action_view_analysis(self):
        analysis_ids = self.mapped('analysis_ids')
        action = self.env["ir.actions.actions"]._for_xml_id("lims.analysis_action")
        if len(analysis_ids) > 1:
            action['domain'] = [('id', 'in', analysis_ids.ids)]
        elif len(analysis_ids) == 1:
            form_view = [(self.env.ref('lims.lims_analysis_view_form').id, 'form')]
            if 'views' in action:
                action['views'] = form_view + [(state, view) for state, view in action['views'] if view != 'form']
            else:
                action['views'] = form_view
            action['res_id'] = analysis_ids.id
        else:
            action = {'type': 'ir.actions.act_window_close'}

        context = {
            'default_company_id': self.env.company.id,
        }
        if len(self) == 1:
            context.update({
                'default_partner_id': self.id,
                'default_user_id': self.env.user.id,
            })
        action['context'] = context
        return action
