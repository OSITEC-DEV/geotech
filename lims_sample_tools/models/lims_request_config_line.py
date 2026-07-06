# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class LimsRequestConfigLine(models.Model):
    _name = 'lims.request.config.line'
    _description = 'Analysis Request Configuration'

    sample_line_id = fields.Many2one('lims.sample.line', string='Request Line')
    product_id = fields.Many2one('product.product', string='Parameter', required=True)
    quantity = fields.Float('Quantity', default=1.0, help='Sample quantity from the request line')
    frequency = fields.Integer('Frequency', default=1)
    department_id = fields.Many2one('lims.department', string='Department/Subcontractor')
    to_subcontract = fields.Boolean('To subcontract')
    main_id = fields.Many2one('lims.sample.main', string='Request')
    sale_id = fields.Many2one('sale.order', string='Sale Order', ondelete='set null', index=True)
    income_account_id = fields.Many2one('account.account', string='Accounting Account',
                                        help='Set manually if this line needs a specific income account; '
                                             'otherwise the product/department defaults apply as usual.')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company.id)
    request_category = fields.Selection(related='main_id.request_category', store=True, readonly=True)

    @api.onchange('main_id')
    def _onchange_main_id(self):
        if self.main_id:
            products = self.main_id.sample_line.mapped('product_ids').ids
            return {'domain': {'product_id': [('id', 'in', products)]}}

    @api.onchange('department_id')
    def _onchange_department_suggest_account(self):
        if self.department_id and self.department_id.income_account_id and not self.income_account_id:
            self.income_account_id = self.department_id.income_account_id
        if self.department_id:
            self.to_subcontract = self.department_id.is_subcontractor

    def update_sale_order(self):
        for rec in self:
            sale = rec.main_id.sale_id
            if not sale:
                continue
            line = sale.order_line.filtered(
                lambda l: l.product_id == rec.product_id and not l.display_type
            )
            vals = {
                'product_uom_qty': rec.quantity,
                'price_unit': rec.product_id.lst_price,
            }
            if line:
                line.write(vals)
            else:
                self.env['sale.order.line'].create({
                    'order_id': sale.id,
                    'product_id': rec.product_id.id,
                    'product_uom_qty': rec.quantity,
                    'price_unit': rec.product_id.lst_price,
                    'name': rec.product_id.name,
                })

    @api.constrains('main_id', 'department_id')
    def _check_department_required_on_request(self):
        for rec in self:
            if rec.main_id and not rec.department_id:
                raise ValidationError(
                    'Department is required on config lines linked to an analysis request.'
                )
