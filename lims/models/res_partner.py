# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import pytz
from dateutil import parser
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class ResPartner(models.Model):
    _inherit = 'res.partner'
    _rec_name = 'partner_no'

    main_ids = fields.One2many('lims.sample.main', 'partner_id', string='Reports')
    partner_no = fields.Char('ID number', index=True, copy=False)
    partner_no_category = fields.Selection([
        ('national_id', 'ID national'),
        ('social_security', 'Securité Sociale'),
        ('police', 'Police'),
        ('gendarmerie', 'Gendarmerie'),
        ('customs', 'Douane'),
        ('military', 'Militaire'),
        ('other', 'Autres'),
    ], string="Category")

    def create_new_request(self):
        return {
            'name': _('/'),
            'type': 'ir.actions.act_window',
            'res_model_id': 'lims.sample.main',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'current',
            'context': {'default_partner_id': self.id}
        }

    def action_view_reports(self):
        main_ids = self.mapped('main_ids')
        action = self.env["ir.actions.actions"]._for_xml_id("lims.receiving_samples_action")
        if len(main_ids) > 1:
            action['domain'] = [('id', 'in', main_ids.ids)]
        elif len(main_ids) == 1:
            form_view = [(self.env.ref('lims.lims_view_form').id, 'form')]
            if 'views' in action:
                action['views'] = form_view + [(state, view) for state, view in action['views'] if view != 'form']
            else:
                action['views'] = form_view
            action['res_id'] = main_ids.id
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

    @api.model
    def _name_search(self, name, domain=None, operator='ilike', limit=None, order=None):
        domain = domain or []
        if name:
            # Be sure name_search is symetric to display_name
            name = name.split(' / ')[-1]
            domain = [('name', operator, name)] + domain
            domain = ['|',('phone', operator, name), ('partner_no', operator, name)] + domain
        return self._search(domain, limit=limit, order=order)


    def next_id(self):
        for rec in self:
            rec.ref = self.env['ir.sequence'].next_by_code('res.partner.ref', sequence_date=self.create_date) or _('/')
            return rec.ref


