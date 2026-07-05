# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    translation_template = fields.Many2one('lims.translate.titles', string="Translation Template",
                                           related='company_id.translation_template', readonly=False)
    logo_gov = fields.Binary(string="Logo Gov", related='company_id.logo_gov', readonly=False)
    logo_quality = fields.Binary(string='logo Quality', related='company_id.logo_quality', readonly=False)
    logo_iso = fields.Binary(string='logo ISO', related='company_id.logo_iso', readonly=False)
    signature_consult = fields.Binary("Consultant Signature", related='company_id.signature_consult', readonly=False)
    signature_quality = fields.Binary("QA Signature", related='company_id.signature_quality', readonly=False)
    signature_director = fields.Binary("Director Signature", related='company_id.signature_director', readonly=False)
    split_sample_by_department = fields.Boolean('Split Samples by department',
                                                related='company_id.split_sample_by_department', readonly=False)
    auto_done = fields.Boolean("Mark the result as done after click on save",
                               related='company_id.auto_done', readonly=False)


class LimsTranslateTitles(models.Model):
    _name = 'lims.translate.titles'
    _description = "Dictionary Translator"
    name = fields.Char('Template', required=True)
    title = fields.Char('LABORATORY RESULTS', required=True)
    medical_name = fields.Char('Medical Report Number', required=True)
    national_id = fields.Char('National ID', required=True)
    full_name = fields.Char('FullName', required=True)
    nationality = fields.Char('Nationality', required=True)
    age = fields.Char('Age', required=True)
    blood_group = fields.Char('Blood Group', required=True)
    description = fields.Char('Other note')
    sampling_date = fields.Char('Sampling Date')
    test_name = fields.Char('Test')
    gender = fields.Char('Gender')
    perso_info = fields.Char('Personal Info')
    result = fields.Char('Result')
    range_lims = fields.Char('Range')
    method = fields.Char('Method')