# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
import math as m
import statistics as s
from odoo.exceptions import UserError, ValidationError
import json


class LimsBatchAnalysis(models.TransientModel):
    _inherit = 'lims.batch.analysis'


    def _prepare_batch_data(self):
        for rec in self:
            # Filter draft analyses

            # Collect unique department_ids to ensure they match
            department_ids = set(analysis.department_id.id for analysis in rec.analysis_ids if analysis.department_id)
            if len(department_ids) > 1:
                raise UserError("All analyses must belong to the same department to create a batch.")

            # Initialize lists for analysis, instrument, and sample data
            analysis_list = []
            instrument_list = []
            sample_set = set()
            insturments = set()
            for analysis in rec.analysis_ids:
                # Add each analysis to the analysis list
                analysis_list.append((4, analysis.id))

                # Get the related equipment from the analysis's method
                if analysis.method_id and analysis.method_id.equipment_id:
                    # Add the instrument to the instrument list
                    insturments.add(analysis.method_id)
                analysis.do_confirm()
                analysis.do_work()
                # Collect sample IDs from the analysis
                if analysis.sample_line_id:
                    sample_set.add(analysis.sample_line_id.id)

            for inst in insturments:
                instrument_list.append((0, 0, {
                    'equipment_id': inst.equipment_id.id,
                    'date': fields.Datetime.now(),
                }))
            # Convert sample_set to list of tuples for Many2many relation
            sample_list = [(4, sample_id) for sample_id in sample_set]

            return {
                'name': self.env['ir.sequence'].next_by_code('lims.batch'),  # Auto-generate batch number if needed
                'date': fields.Datetime.now(),
                'department_id': list(department_ids)[0],
                'analysis_ids': analysis_list,
                'instrument_ids': instrument_list,
                'sample_ids': sample_list,
                'state': 'draft',
            }
    def create_batch(self):
        for rec in self:
            # Create the new batch with analyses, instruments, and samples
            batch = rec.env['lims.batch'].create(self._prepare_batch_data())
            for analysis in rec.analysis_ids:
                analysis.batch_id = batch.id
            # Open the newly created batch form view
            return {
                'name': 'LIMS Batch',
                'type': 'ir.actions.act_window',
                'res_model': 'lims.batch',
                'view_mode': 'form',
                'res_id': batch.id,
                'target': 'current',
            }