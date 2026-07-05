from odoo import fields, models, _, api
from odoo.exceptions import UserError
import json

class LimsReport(models.Model):
    _inherit = 'lims.report'

    disclaimer = fields.Text('Disclaimer')
    limitations = fields.Text('Limitations')

    def _get_default_template_report(self):
        res = self.env.ref('lims_report_templates.lims_portal_report_pdf')
        return res.id if res else False

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('print_group_id',False):
                template_id = self.env['lims.parameter.print.group'].search([('id','=',vals['print_group_id'])],limit=1)
                if template_id.template_id:
                    vals['template_id'] = template_id.template_id.id
                else:
                    raise UserError("Please define a template for reports \n Configuration-->Parameter Print Group")
            vals['disclaimer'] = '\n'.join(item for item in self.get_disclaimer() if self.get_disclaimer())
            vals['limitations'] = '\n'.join(item for item in self.get_limitations() if self.get_limitations())
        return super(LimsReport, self).create(vals_list)

    template_id = fields.Many2one('ir.actions.report','Template',domain=[('model','=','lims.report')]
                                  ,required=True,default=_get_default_template_report)

    def get_limitations(self):
        return list(
            set(analysis.product_id.limitations for analysis in self.analysis_ids if analysis.product_id.limitations))

    def get_disclaimer(self):
        return list(
            set(analysis.product_id.disclaimer for analysis in self.analysis_ids if analysis.product_id.disclaimer))