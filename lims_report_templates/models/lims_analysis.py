# -*- coding: utf-8 -*-

import json

from odoo import api, fields, models


@api.model
def _lang_get(self):
    return self.env['res.lang'].get_installed()


class LimsAnalysis(models.Model):
    _inherit = 'lims.analysis'

    @api.model
    def default_get(self, default_fields):
        values = super().default_get(default_fields)
        if 'lang' in default_fields:
            values['lang'] = values.get('lang') or self.env.lang
        return values

    @api.model_create_multi
    def create(self, vals):
        if 'company_id' in vals:
            self = self.with_company(vals['company_id'])
        if 'product_id' in vals:
            default_template = self.env['product.product'].browse(vals['product_id'])['default_template']
            vals['lim_ana_report'] = default_template.id if default_template else False
            vals['eng_text'] = default_template.eng_text if default_template else False
        return super(LimsAnalysis, self).create(vals)

    lim_ana_report = fields.Many2one('lims.analysis.report', string='Report Template', tracking=True)
    eng_text = fields.Html('Result & Interpretation')
    ar_text = fields.Html('Arabic Comments')

    domain_test = fields.Char(compute='compute_domains', readonly=True)
    lang = fields.Selection(_lang_get, string='Language',
                            help="All the emails and documents sent to this contact will be translated in this language.")

    @api.onchange('lim_ana_report')
    def get_template(self):
        for rec in self:
            if rec.lim_ana_report.eng_text:
                res = ""
                field = ""
                kr_print = ""
                # CLEANR = re.compile('<.*?>')
                eng_text = rec.lim_ana_report.eng_text
                # ar_text = re.sub(CLEANR, '', rec.lim_ana_report.ar_text )
                # oussama code
                dict_id = rec.lim_ana_report.dict_id.dict_key_ids
                for dict_line in dict_id:
                    if dict_line.key in eng_text:
                        field_child = dict_line.field_child
                        try:
                            if field_child:
                                field_name = dict_line.field_id.name + '.' + field_child
                            else:
                                field_name = dict_line.field_id.name
                            field = self.mapped(field_name)
                        except:
                            raise ('Invalid field')
                        if isinstance(field, list):
                            field = field[0]
                        else:
                            field = field['name']
                        eng_text = eng_text.replace(dict_line.key, str(field))
                if '#result#' in eng_text:
                    for input in rec.input_result_ids.filtered(
                            lambda i: i.state == 'reviewed' and i.name.code != '#kr#'):
                        if input.result:
                            res += str(input.name.name) + str(": ") + input.result + "<br>"
                kr = rec.input_result_ids.filtered(lambda i: i.state == 'reviewed' and i.name.code == '#kr#')
                if '#kr#' in eng_text and kr:
                    kr_print = kr[0].result
                rec.eng_text = eng_text.replace('#result#', res).replace('#kr#', kr_print)

    @api.depends('product_id')
    def compute_domains(self):
        for rec in self:
            rec.domain_test = json.dumps([('product_ids', 'in', rec.product_id.ids)]) if rec.product_id else "[]"

    def get_min_max_references(self):
        res = {}
        range_ids = self.get_references()
        if range_ids:
            for r in range_ids:
                if self.uom_id == r.uom_id and r.status.code == 'OK':
                    res = {
                        'min': r.min_val,
                        'max': r.max_val
                    }
        else:
            res = {
                'min': 0.0,
                'max': 0.0
            }
        return res
