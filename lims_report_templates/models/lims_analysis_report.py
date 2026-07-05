# -*- coding: utf-8 -*-

from odoo import api, fields, models

from .auto_translate import translate


class LimsReportSections(models.Model):
    _name = 'lims.report.section'
    _order = "sequence"
    _description = "Report sections"
    name = fields.Char('English Section Name', required=True)
    name_ar = fields.Char('Arabic Section Name')
    sequence = fields.Integer('Section Sequence', default=1)
    report_id = fields.Many2one('lims.analysis.report')

    @api.onchange('name')
    def onchange_name(self):
        for rec in self:
            gtn = translate(rec.name, 'ar', 'en') if rec.name else ""
            rec.name_ar = str(gtn) or rec.name


class LimsAnalysisReport(models.Model):
    _name = 'lims.analysis.report'
    _description = "Lims report Template"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'

    name = fields.Char('Template Name')
    product_ids = fields.Many2many('product.product', 'product_report_template_rel',
                                   'product_id', 'report_template_id', string='Parameters',
                                   domain=[('type', '=', 'service'), ('isParameter', '=', True)])
    eng_text = fields.Html('English Comments')
    ar_text = fields.Html('Arabic Comments')

    section_ids = fields.One2many('lims.report.section', 'report_id', string="Sections")
    # oussama code
    dict_id = fields.Many2one('lims.report.keys', string="Dictionary")

    def get_english_html(self):
        temp = """"""
        for rec in self:
            rec = rec.with_context(lang="en_US")
            for section in rec.section_ids:
                trans_name = section.name
                temp += "<div style='border-top:2px solid black;'><h3>" + trans_name + "</h3>"
                temp += "<br/><br/></div>"

        return temp

    def get_arabic_html(self):
        temp = """"""
        for rec in self:
            rec = rec.with_context(lang="ar_001")
            for section in rec.section_ids:
                trans_name = section.name_ar if section.name_ar else ""
                temp += "<div  style='border-top:2px solid black;text-align: right;'><h3>" + trans_name + "</h3>"
                temp += "<br/><br/></div>"
        return temp

    @api.onchange('section_ids')
    def onchange_sections(self):
        for rec in self:
            rec.eng_text = rec.get_english_html()
            rec.ar_text = rec.get_arabic_html()
