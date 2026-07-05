# -*- coding: utf-8 -*-
from odoo import api, fields, models


class LimsCreatePackWizard(models.TransientModel):
    _name = 'lims.create.pack.wizard'
    _description = 'Create Package from Parameters'

    name = fields.Char('Package Name', required=True)
    product_ids = fields.Many2many(
        'product.product',
        string='Parameters',
        domain=['|', ('isParameter', '=', True), ('isPack', '=', True)],
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        active_ids = self.env.context.get('active_ids', [])
        if active_ids:
            res['product_ids'] = [(6, 0, active_ids)]
        return res

    def _get_pack_vals(self):
        uom = self.env.ref('uom.product_uom_unit', raise_if_not_found=False)
        return {
            'name': self.name,
            'isPack': True,
            'type': 'service',
            'child_ids': [(6, 0, self.product_ids.ids)],
            'department_ids': [(6, 0, self.product_ids.mapped('department_ids').ids)],
            'uom_id': uom.id if uom else False,
            'uom_po_id': uom.id if uom else False,
        }

    def action_create_pack(self):
        self.ensure_one()
        pack = self.env['product.template'].create(self._get_pack_vals())
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'product.template',
            'res_id': pack.id,
            'view_mode': 'form',
            'target': 'current',
        }
