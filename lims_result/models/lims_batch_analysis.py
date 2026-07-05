# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
import math as m
import statistics as s
from odoo.exceptions import UserError, ValidationError
import json


class LimsBatchAnalysis(models.TransientModel):
    _name = 'lims.batch.analysis'
    _description = 'lims batch Analysis Table'

    method_id = fields.Many2one('lims.method', 'Instrument')
    user_id = fields.Many2one('res.users', 'Assinged To')
    sample_ids = fields.Many2many('lims.sample.preparation', 'batch_sample_rel',
                                  'batch_id', 'sample_id', string='Sample ID')
    analysis_ids = fields.Many2many('lims.analysis', string='Tests')

    @api.onchange('sample_ids')
    def onchange_sample_ids(self):
        for rec in self:
            if rec.sample_ids:
                rec.analysis_ids = False
                analysis = rec.sample_ids.mapped('analysis_ids').filtered(lambda self:
                                                                          self.state not in ['valid']
                                                                          and self.department_id.id in self.env.user.department_ids.ids)
                rec.analysis_ids = analysis.ids if analysis else []

    @api.onchange('method_id', 'analysis_ids')
    def onchange_method_id(self):
        for rec in self:
            if rec.method_id:
                for a in rec.analysis_ids:
                    if rec.method_id.id in a.product_id.method_ids.ids:
                        a.method_id = rec.method_id.id
                    else:
                        pass

    @api.onchange('user_id')
    def onchange_user_id(self):
        for rec in self:
            if rec.user_id:
                for a in rec.analysis_ids:
                    a.user_id = rec.user_id.id

    def do_assign(self):
        for rec in self:
            for analysis in rec.analysis_ids.filtered(lambda self: self.state == 'draft'):
                if not analysis.method_id:
                    raise UserError("Please assign instrument to: " + analysis.sample_line_id.name)
                analysis.do_confirm()
            return {
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'lims.batch.analysis',
                'target': 'new',
                'res_id': rec.id,
                'default_analysis_ids': rec.analysis_ids.ids,
                'default_sample_ids': rec.sample_ids.ids
            }

    def do_wip(self):
        for rec in self:
            for analysis in rec.analysis_ids.filtered(lambda self: self.state == 'todo'
                                                                   and self.user_id.id == self.env.user.id):
                analysis.do_work()
            return {
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'lims.batch.analysis',
                'target': 'new',
                'res_id': rec.id,
                'default_analysis_ids': rec.analysis_ids.ids
            }

    def do_validate(self):
        for rec in self:
            for analysis in rec.analysis_ids.filtered(lambda self: self.state == 'done'):
                analysis.do_validate()

    def save_close(self):
        for rec in self:
            rec.ensure_one()
        # close popup
        return {'type': 'ir.actions.act_window_close'}
