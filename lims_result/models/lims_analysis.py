# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
import math as m
import statistics as s
from odoo.exceptions import UserError, ValidationError

import requests, json


class LimsAnalysis(models.Model):
    _inherit = 'lims.analysis'

    json_report = fields.Json("Json Report")

    @api.depends('method_id', 'result_num', 'uom_id')
    def return_critical_result(self):
        for record in self:
            if record.state not in ['draft', 'cancel']:
                rang_result = record.get_references()
                if record.type_result == 'num':
                    if len(rang_result):
                        for rang in rang_result:
                            if record.uom_id == rang.uom_id:
                                if (rang.max_critical and record.result_num >= rang.max_critical) \
                                        or (rang.min_critical and record.result_num <= rang.min_critical):
                                    record.is_critical = True
                                else:
                                    record.is_critical = False
                                break
                            else:
                                record.is_critical = False
                else:
                    return False
            else:
                record.is_critical = False

    @api.depends("product_id")
    def onchange_calculated_result(self):
        for a in self:
            result = 0.0
            if a.product_id.is_calculated:
                formula = a.product_id.formula
                corresp_ids = a.product_id.mapped('correspondence_ids')
                for corresp in corresp_ids:
                    validated_analysis = a.main_id.mapped('analysis_ids').filtered(lambda s: s.id != a.id and \
                                                                                             s.product_id.id in corresp.parameter_id.product_variant_id.ids)
                    if validated_analysis and all(v.state in ['done', 'valid'] for v in validated_analysis):
                        if corresp.code in formula:
                            result = validated_analysis[0].result_num
                            formula = formula.replace('[' + corresp.code + ']', str(result))
                        formula = formula.replace('[age]', str(a.partner_id.age)) if '[age]' in formula else formula
                        formula = formula.replace('[weight]',
                                                  str(a.partner_id.weight)) if '[weight]' in formula else formula

                        if '[volume]' in formula:
                            volume = a.input_result_ids.filtered(lambda i: i.name.code == "#volume#")
                            if volume and volume.result:
                                formula = formula.replace('[volume]', str(volume.result))
                            else:
                                a.computed_result = 0.0
                                return a.computed_result
                    else:
                        a.computed_result = 0.0
                        return 0.0
                a.computed_result = float(eval(formula))
            else:
                a.computed_result = 0.0

    last_result = fields.Char('last result', readonly=True)
    is_critical = fields.Boolean('Is Critical', compute='return_critical_result', store='True', copy=False,
                                 tracking=True)
    action_todo = fields.Many2one('mail.activity.type', 'Action todo')
    input_result_ids = fields.One2many('lims.result.input', 'analysis_id', string='Input results')
    computed_result = fields.Float('Computed result', compute='onchange_calculated_result')
    related_analysis = fields.Many2one('lims.analysis', string="Related analysis", tracking=True, copy=False)
    is_calculated = fields.Boolean('Calculated test')

    def get_last_result(self):
        result = self.partner_id.analysis_ids.filtered(
            lambda a: a.product_id.id == self.product_id.id and a.state == 'valid'
                      and (a.date_result and self.create_date > a.date_result) and a.id != self.id
        ).sorted(key=lambda a: a.id, reverse=True)

        if result:
            last_result_txt = result[0].result_txt or "NA"  # Ensure result_txt is always a string
            last_result_date = result[0].date_result.strftime("%d/%m/%Y") if result[0].date_result else "Unknown Date"

            self.last_result = f"{last_result_txt} On {last_result_date}"
            return self.last_result

    @api.model_create_multi
    def create(self, vals):
        values = []
        result = super(LimsAnalysis, self).create(vals)
        input_result_ids = result.product_id.mapped('input_result_ids')
        if input_result_ids and result.product_id.do_generate_inputs:
            for input in input_result_ids:
                values.append(
                    (0, 0, {'name': input.id, 'state': 'draft'}))
            result.write({'input_result_ids': values})
        if result.product_id.is_calculated:
            result.is_calculated = True
            corresp = result.product_id.mapped('correspondence_ids')['parameter_id']
            existing_parameters = result.main_id.mapped('analysis_ids').filtered(lambda a: a.state != ' cancel')[
                'product_id']
            for c in corresp.product_variant_id:
                if c not in existing_parameters:
                    values = {
                        'product_id': c.id,
                        'main_id': result.main_id.id,
                        'sample': result.sample.id,
                        'sample_line_id': result.sample_line_id.id,
                        'partner_id': result.partner_id.id,
                        'related_analysis': result.id,
                        'technique_id': c.default_method_id.id if c.default_method_id else False
                    }
                    self.env['lims.analysis'].create(values)
        result.get_last_result()
        return result

    def do_done(self):
        if self.is_calculated and self.computed_result:
            self.result_num = self.computed_result
            self.result_txt = str(self.computed_result) + ' ' + str(self.uom_id.name)
        if not self.action_todo and self.is_critical:
            raise UserError(("Critical result = %s for test %s, sample: %s") %
                            (self.result_num, self.product_id.name, self.sample_line_id.name,))
        return super(LimsAnalysis, self).do_done()

    def open_batch_analysis(self):
        return {
            'name': _('Batch Analysis Table'),
            'type': 'ir.actions.act_window',
            'res_model': 'lims.batch.analysis',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_analysis_ids': self.ids, 'user_id': False}
        }

    def do_review_all_result_input(self):
        for record in self:
            for input in record.input_result_ids:
                input.reviewed()

    def send_analysis_result(self):
        # base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        url = "http://127.0.0.1:10017/api/lims/analysis/JSON/upload"

        headers = {"Content-Type": "application/json"}
        data = {
            "sample_code": "25-02-0001",
            "pH": 7.2,
            "moisture_content": 12.5,
            "protein": 8.9,
            "fat": 4.2,
            "sugar": 5.6,
            "heavy_metals": {
                "lead": 0.02,
                "mercury": 0.005,
                "cadmium": 0.01
            },
            "pesticide_residue": {
                "chlorpyrifos": 0.03,
                "glyphosate": 0.07
            },
            "microbiology": {
                "total_coliforms": 100,
                "e_coli": 0,
                "salmonella": "Not Detected"
            }
        }

        response = requests.post(url, headers=headers, json=json.dumps(data))
        # response.raise_for_status()  # Raise an error for bad responses (4xx, 5xx)
        print("Response:", response.json())


class LimsResultRange(models.Model):
    _inherit = 'lims.result.range'

    min_critical = fields.Float("Critical Low", digits=(16, 4))
    max_critical = fields.Float("Critical High", digits=(16, 4))


class LimsResultInput(models.Model):
    _name = "lims.result.input"
    _description = "Lims Result Multi Inputs"

    name = fields.Many2one("lims.result.input.type")
    result = fields.Char('Result')
    state = fields.Selection([('draft', 'Draft'), ('reviewed', 'Reviewed')], default='draft')
    analysis_id = fields.Many2one('lims.analysis', 'Analysis')
    reviewed_by = fields.Many2one('res.users', "Users")

    def reviewed(self):
        for record in self:
            record.state = 'reviewed'
            record.reviewed_by = record.env.user.id

    def unlink(self):
        for result in self:
            if result.analysis_id.state == 'valid':
                raise UserError(_('You can not delete a results of analysis test.'))
        return super(LimsResultInput, self).unlink()


class LimsResultInputType(models.Model):
    _name = "lims.result.input.type"
    _description = "Lims Result Input Type"
    name = fields.Char("Input result")
    code = fields.Char("Code")


