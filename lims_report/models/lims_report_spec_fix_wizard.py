# -*- coding: utf-8 -*-
from odoo import api, fields, models


class LimsReportSpecFixWizard(models.TransientModel):
    """Wizard that lets a reporter correct the limit and/or specification
    on a single lims.analysis row from the final report form."""
    _name = 'lims.report.spec.fix.wizard'
    _description = 'Fix Limit & Specification'

    analysis_id = fields.Many2one(
        'lims.analysis', string='Analysis', required=True, readonly=True,
        ondelete='cascade',
    )
    # Read-only context fields shown to the reporter
    analyte_name = fields.Char(
        string='Analyte',
        related='analysis_id.product_id.name',
        readonly=True,
    )
    product_id = fields.Many2one(
        'product.product',
        related='analysis_id.product_id',
        readonly=True,
        store=False,
    )
    current_specification = fields.Char(
        string='Current Specification',
        related='analysis_id.specification',
        readonly=True,
    )

    # Editable fields
    limit_id = fields.Many2one(
        'lims.analysis.limit',
        string='Limit',
        domain="[('product_id', '=', product_id)]",
        help="Select the correct limit. Specification will be recomputed automatically.",
    )
    specification = fields.Char(
        string='Specification Override',
        help="Leave blank to let the system compute it from the selected limit. "
             "Fill in manually only if no matching limit record exists.",
    )

    def action_apply(self):
        """Write the chosen limit and/or specification back to the analysis."""
        self.ensure_one()
        analysis = self.analysis_id

        if self.limit_id:
            # Link the limit — write override will call _refresh_specification
            analysis.write({'limit_id': self.limit_id.id})
            # Belt-and-suspenders: call directly in case write override was skipped
            if hasattr(analysis, '_refresh_specification'):
                analysis._refresh_specification()
            # Manual override wins if the reporter also typed something
            if self.specification:
                analysis.write({'specification': self.specification})
        else:
            # No limit — apply manual spec override if provided
            if self.specification is not False and self.specification is not None:
                analysis.write({'specification': self.specification or ''})

        return {'type': 'ir.actions.act_window_close'}
