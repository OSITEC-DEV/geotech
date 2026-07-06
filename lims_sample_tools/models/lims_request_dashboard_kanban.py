# -*- coding: utf-8 -*-
from odoo import models, fields


class LimsRequestDashboardKanban(models.Model):
    _name = 'lims.request.dashboard.kanban'
    _description = 'LIMS Request Dashboard'
    _order = 'sequence'

    name = fields.Char('Name')
    request_category = fields.Selection([
        ('private', 'Private'),
        ('government', 'Government'),
        ('project', 'Project'),
    ], required=True)

    request_ids = fields.One2many(
        'lims.sample.main', compute='_compute_request_ids', string='Requests'
    )
    sequence = fields.Integer('Sequence')
    draft_count = fields.Integer(compute='_compute_counts')
    confirm_count = fields.Integer(compute='_compute_counts')
    recieved_count = fields.Integer(compute='_compute_counts')
    progress_count = fields.Integer(compute='_compute_counts')
    tosend_count = fields.Integer(compute='_compute_counts')
    done_count = fields.Integer(compute='_compute_counts')
    reject_count = fields.Integer(compute='_compute_counts')
    total_count = fields.Integer(compute='_compute_total')

    def _compute_total(self):
        for rec in self:
            rec.total_count = sum([
                rec.draft_count, rec.confirm_count, rec.recieved_count,
                rec.progress_count, rec.tosend_count, rec.done_count, rec.reject_count,
            ])

    def _compute_request_ids(self):
        for rec in self:
            rec.request_ids = self.env['lims.sample.main'].search([
                ('request_category', '=', rec.request_category)
            ])

    def _compute_counts(self):
        for rec in self:
            domain = [('request_category', '=', rec.request_category)]
            data = self.env['lims.sample.main'].read_group(domain, ['state'], ['state'])
            mapped = {d['state']: d['state_count'] for d in data}
            rec.draft_count = mapped.get('draft', 0)
            rec.confirm_count = mapped.get('confirm', 0)
            rec.recieved_count = mapped.get('recieved', 0)
            rec.progress_count = mapped.get('progress', 0)
            rec.tosend_count = mapped.get('tosend', 0)
            rec.done_count = mapped.get('done', 0)
            rec.reject_count = mapped.get('reject', 0)

    def action_open_requests(self, state):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'{self.name} - {state}',
            'res_model': 'lims.sample.main',
            'view_mode': 'list,form',
            'domain': [
                ('request_category', '=', self.request_category),
                ('state', '=', state),
            ],
            'context': {'default_request_category': self.request_category},
        }

    def action_open_draft(self):
        return self.action_open_requests('draft')

    def action_open_confirm(self):
        return self.action_open_requests('confirm')

    def action_open_recieved(self):
        return self.action_open_requests('recieved')

    def action_open_progress(self):
        return self.action_open_requests('progress')

    def action_open_tosend(self):
        return self.action_open_requests('tosend')

    def action_open_done(self):
        return self.action_open_requests('done')

    def action_open_reject(self):
        return self.action_open_requests('reject')

    def action_create_request(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'New Request',
            'res_model': 'lims.sample.main',
            'view_mode': 'form',
            'target': 'current',
            'context': {'default_request_category': self.request_category},
        }
