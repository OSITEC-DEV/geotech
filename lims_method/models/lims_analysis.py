# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class LimsAnalysis(models.Model):
    _inherit = 'lims.analysis'


    def _get_default_equipment_by_company(self):
        if self.method_id:
            domain = [('instrument_id','=', self.method_id.id),('company_id','=',self.company_id.id)]
            instrument_id = self.env['maintenance.equipment'].search(domain,limit=1)
            self.equipment_id = instrument_id.id
        return False

    @api.depends('method_id')
    def onchange_technique(self):
        for rec in self:
            method_id = rec.method_id
            # raise UserError(method_id.method_technique_ids)
            if method_id:
                rec.domain_technique = json.dumps(
                    [('id', 'in', method_id.method_technique_ids.ids)]) if method_id.method_technique_ids else "[]"
            else:
                rec.domain_technique = []

    @api.onchange('method_id')
    def onchange_method_equipment(self):
        for record in self:
            domain = [('instrument_id', '=', record.method_id.id), ('company_id', '=', record.company_id.id)]
            instrument_id = record.env['maintenance.equipment'].search(domain, limit=1)
            record.equipment_id = instrument_id.id


    step_ids = fields.One2many('lims.analysis.step', 'analysis_id', 'Steps Todo')
    technique_id = fields.Many2one('lims.method.technique', "Method/Technique")
    domain_technique = fields.Char(compute='onchange_technique', store=False, readonly=True)
    equipment_id = fields.Many2one('maintenance.equipment', "Equipment",
                                default= lambda self:self._get_default_equipment_by_company(),
                                domain=[('used_inlab', '=', True),('instrument_id','=',lambda self:self.method_id.id)])


    @api.depends('step_ids')
    def compute_hide_result(self):
        for record in self:
            res = super(LimsAnalysis, record).compute_hide_result()
            steps = self.step_ids.filtered(lambda s: s.state != 'cancel')
            if steps:
                if all(step.state == 'validated' for step in steps):
                    record.hide_result = res = False
                else:
                    record.hide_result = res = True
            else:
                return res
            return res

    # def do_work(self):
    #     res = super(LimsAnalysis, self).do_work()
    #     values = []
    #     old_steps = self.env['lims.analysis.step'].search([('analysis_id', '=', self.id),('state','!=','validated')])
    #     for os in old_steps:
    #         os.sudo().do_cancel()
    #     if self.product_id.required_method:
    #         step_ids = self.technique_id.mapped('method_step_ids') if self.technique_id else False
    #         if step_ids:
    #             for step in step_ids:
    #                 values.append(
    #                     (0, 0, {'step_id': step.id,
    #                             'state': 'wip',
    #                             'equipment_id': step.default_equipment_id.id,
    #                             'user_id': step.user_id.id}))
    #         if not self.technique_id:
    #             raise ValidationError(_('Please select the method used in this Test'))
    #     self.sudo().write({'step_ids': values})
    #     return res

    def do_validate(self):
        res = super(LimsAnalysis, self).do_validate()
        for step in self.step_ids.filtered(lambda s: s.state != 'cancel'):
            step.do_validate()
        return res


class LimsAnalysisStep(models.Model):
    _name = 'lims.analysis.step'
    _rec_name = 'name'
    _description = "Steps of analysis"

    @api.depends('step_id', 'analysis_id')
    def get_display_name(self):
        for record in self:
            if record.step_id and record.analysis_id:
                record.name = record.step_id.name + '-' + record.analysis_id.sample_line_id.display_name
            else:
                record.name = '/'

    name = fields.Char(compute='get_display_name')
    analysis_id = fields.Many2one('lims.analysis', 'Analysis')
    sample_id = fields.Many2one('lims.sample.preparation', related='analysis_id.sample_line_id')
    step_id = fields.Many2one('lims.method.step', 'Step')
    state = fields.Selection(
        [('wip', 'In progress'), ('done', 'Done'), ('validated', 'Validated'), ('cancel', 'Canceled')], default='wip')
    attachment = fields.Binary('Add Attachment')
    remarks = fields.Many2one('lims.analysis.remarks', string='Remarks')
    note = fields.Char('Note')
    user_id = fields.Many2one('res.users', 'Analyst', related='analysis_id.user_id')
    equipment_id = fields.Many2one('maintenance.equipment', 'Equipment', domain=[('used_inlab', '=', True)])
    sub_sample_id = fields.Many2one('lims.sub.sample.preparation', 'Sub-Sample')
    domain_sample = fields.Char(compute='onchange_sub_sample_domain', store=False, readonly=True)
    domain_analysts = fields.Char(compute='onchange_sub_sample_domain', store=False, readonly=True)
    user_id = fields.Many2one('res.users', 'Assigned to')
    done_by = fields.Many2one('res.users', 'Done by')
    done_date = fields.Datetime('Done date',readonly=True)
    validate_date = fields.Datetime('Validate date',readonly=True)
    @api.depends('sample_id')
    def onchange_sub_sample_domain(self):
        for rec in self:
            rec.domain_sample = json.dumps(
                [('id', 'in', rec.sample_id.subsample_ids.ids)]) if rec.sample_id.subsample_ids else "[]"
            rec.domain_analysts = json.dumps(
                [(
                 'department_ids', 'in', rec.analysis_id.department_id.ids)]) if rec.analysis_id.department_id else "[]"

    def do_done(self):
        for record in self:
            this_step = record.step_id
            pending_steps = record.analysis_id.step_ids.filtered(lambda s: s.step_id.need_approve and
                                                                           s.step_id.id != this_step.id and
                                                                           s.step_id.sequence < this_step.sequence and
                                                                           s.state != 'validated'
                                                                 )
            if not len(pending_steps):
                record.state = 'done'
                record.done_by = record.env.user.id
                record.done_date = fields.Datetime.now()
            else:
                raise ValidationError("One or more steps must be validated before finishing this step.")

    def do_validate(self):
        for record in self:
            if record.env.user.has_group('lims.group_lims_responsible'):
                record.state = 'validated'
                record.validate_date = fields.Datetime.now()
    def do_cancel(self):
        for record in self:
            record.state = 'cancel'
            record.done_date = False
            record.done_by = False


class LimsAnalysisRemarks(models.Model):
    _name = 'lims.analysis.remarks'
    _rec_name = 'name'
    _description = "Analysis Remarks"

    name = fields.Char('Remarks')
    active = fields.Boolean('Active', default=True)