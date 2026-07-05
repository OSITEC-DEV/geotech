# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models
from odoo.exceptions import UserError


class LimsSampleMain(models.Model):
    _inherit = 'lims.sample.main'

    def _prepare_analysis_line(self, sample, parameter, pack, **kwargs):
        res = super()._prepare_analysis_line(sample, parameter, pack, **kwargs)

        # department = kwargs.get('department')
        # is_subcontracted = kwargs.get('is_subcontracted')

        res.update({
            'technique_id': parameter.default_method_id.id
        })

        return res