# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class LimsSampleWizard(models.TransientModel):
    _name = 'lims.sample.wizard'
    _description = 'Bulk Sample Edit Wizard'

    main_id = fields.Many2one('lims.sample.main', string='Request', readonly=True)
    sample_ids = fields.Many2many('lims.sample.preparation', string='Samples')

    note = fields.Char(string='Note')
    user_id = fields.Many2one('res.users', string='Collector')
    sample_date = fields.Datetime(string='Collected Sample Date')
    receiving_date = fields.Datetime(string='Received on')

    @api.constrains('sample_date', 'receiving_date')
    def _check_dates(self):
        for rec in self:
            if not rec.sample_date or not rec.receiving_date:
                continue
            if rec.sample_date > rec.receiving_date:
                raise ValidationError('Collected sample date cannot be after the receiving date.')

    def _prepare_sample_vals(self):
        vals = {}
        if self.note:
            vals['note'] = self.note
        if self.user_id:
            vals['user_id'] = self.user_id.id
        if self.sample_date:
            vals['sample_date'] = self.sample_date
        if self.receiving_date:
            vals['receiving_date'] = self.receiving_date
        return vals

    def _get_samples_from_context(self):
        raw = self.env.context.get('default_sample_ids')
        if not raw:
            return self.env['lims.sample.preparation']
        first = raw[0]
        if isinstance(first, (list, tuple)) and len(first) == 3 and first[0] == 6:
            ids = first[2]
        else:
            ids = raw
        return self.env['lims.sample.preparation'].browse(ids)

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        samples = self._get_samples_from_context()
        if not samples:
            return res
        sample = samples[0]
        res.update({
            'note': sample.note,
            'user_id': sample.user_id.id if sample.user_id else False,
            'sample_date': sample.sample_date,
            'receiving_date': sample.receiving_date,
        })
        return res

    @api.onchange('note', 'user_id', 'sample_date', 'receiving_date')
    def _onchange_fill_samples(self):
        vals = self._prepare_sample_vals()
        for sample in self.sample_ids:
            sample.update(vals)

    def action_apply(self):
        self.ensure_one()
        self._check_dates()
        vals = self._prepare_sample_vals()
        if vals:
            self.sample_ids.write(vals)
