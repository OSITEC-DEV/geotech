# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
import math as m
import statistics as s
from odoo.exceptions import UserError, ValidationError
import json


class LimsBatchInstrument(models.Model):
    _name = 'lims.batch.equipment'
    _description = 'Lims Batch Equipment'

    equipment_id = fields.Many2one("maintenance.equipment", "Instrument", domain="[('used_inlab','=',True)]")
    date = fields.Datetime("Date")
    batch_id = fields.Many2one("lims.batch", string="Batch number", required=True)
    company_id = fields.Many2one('res.company', 'Company')


class LimsBatchOperators(models.Model):
    _name = 'lims.batch.operators'
    _description = 'Lims Batch Operators'

    operator_id = fields.Many2one("hr.employee", "Operator")
    duration = fields.Float("Duration")
    batch_id = fields.Many2one("lims.batch", string="Batch number", required=True)
    company_id = fields.Many2one('res.company', 'Company')


class LimsBatchReagents(models.Model):
    _name = 'lims.reagents'
    _description = 'Lims Batch Reagents'

    batch_id = fields.Many2one("lims.batch", string="Batch number", required=True)
    product_id = fields.Many2one("product.product", "Reagent")

    lot_id = fields.Many2one("stock.lot", "Lot/Part number",
                             domain="[('product_id', '=', product_id), ('product_qty', '>', 0)]")
    date = fields.Datetime("Date")
    company_id = fields.Many2one('res.company', 'Company')
    is_consumed = fields.Boolean("Consumed", readonly=True)


class LimsBatchConsumableComponent(models.Model):
    _name = 'lims.batch.consumable.component'
    _description = 'Lims Batch Consumable Components'

    @api.depends('quantity', 'product_id')
    def _compute_total_cost(self):
        for line in self:
            line.cost_per_unit = line.product_id.standard_price * line.quantity

    type = fields.Selection([('Reagent', 'Reagent'),
                             ('Consumable', 'Consumable'),
                             ('Labor', 'Labor'),
                             ('Instrument', 'Instrument'),
                             ('utility', 'Utility'),
                             ], string="Type", required=True)
    product_id = fields.Many2one("product.product", string="Product", required=True)
    quantity = fields.Float("Quantity", default=1.0, digits='Batch cost')
    uom_id = fields.Many2one('uom.uom', string='Unit of Measure')
    cost_per_unit = fields.Float("Cost", compute="_compute_total_cost")
    batch_id = fields.Many2one("lims.batch", string="Batch number", required=True)
    is_consumed = fields.Boolean("Consumed", readonly=True)


class LimsBatch(models.Model):
    _name = 'lims.batch'
    _description = 'Lims Batch'

    @api.depends('operator_ids')
    def _compute_labor_cost(self):
        total_cost = 0.0
        for batch in self:
            for operator in batch.operator_ids:
                gross_salary = operator.operator_id.gross_salary
                calendar = operator.operator_id.resource_calendar_id
                weeks_per_month = 4.33
                weekdays = 5
                if calendar and gross_salary:
                    cost_per_hour = gross_salary / (calendar.hours_per_day * weekdays * weeks_per_month)
                    total_cost += cost_per_hour * operator.duration

            batch.labor_cost = total_cost

    @api.depends('labor_cost', 'batch_component_ids')
    def _compute_total_cost(self):
        for batch in self:
            total_component_cost = sum(component.cost_per_unit for component in batch.batch_component_ids)
            batch.total_cost = total_component_cost + batch.labor_cost

    name = fields.Char("Batch Number", required=True, copy=False)
    date = fields.Datetime("Batch date")
    sample_ids = fields.Many2many("lims.sample.preparation", "Samples")
    analysis_ids = fields.Many2many("lims.analysis", "Analysis")
    instrument_ids = fields.One2many("lims.batch.equipment", "batch_id", "Instruments")
    operator_ids = fields.One2many("lims.batch.operators", "batch_id", "Operators")
    reagents = fields.One2many("lims.reagents", "batch_id", "Reagents")
    moves_ids = fields.One2many("stock.move.line", "batch_id", "Stock moves")
    picking_id = fields.Many2one("stock.picking", string="Consumption ID")
    company_id = fields.Many2one('res.company', 'Company')
    department_id = fields.Many2one("lims.department", "Department")
    batch_kit_id = fields.Many2one('lims.batch.kit', string="Batch Kit")
    batch_component_ids = fields.One2many('lims.batch.consumable.component', 'batch_id', string="Batch Components")

    state = fields.Selection([
        ('draft', 'Draft'),
        ('progress', 'WIP'),
        ('done', 'Done'),
        ('cancel', 'Cancel')
    ], default='draft', string="Status")
    total_cost = fields.Float("Batch Cost", compute="_compute_total_cost", store=True)
    labor_cost = fields.Float("Labor Cost", compute="_compute_labor_cost", store=True)

    def action_open_analysis(self):
        """Opens the list of analyses linked to the record."""
        self.ensure_one()
        return {
            'name': "Analyses",
            'type': 'ir.actions.act_window',
            'view_mode': 'list,form',
            'res_model': 'lims.analysis',
            'domain': [('id', 'in', self.analysis_ids.ids)],
            'context': {'default_batch_id': self.id},
        }

    def action_open_samples(self):
        """Opens the list of samples linked to the record."""
        self.ensure_one()
        return {
            'name': "Samples",
            'type': 'ir.actions.act_window',
            'view_mode': 'list,form',
            'res_model': 'lims.sample.preparation',
            'domain': [('id', 'in', self.sample_ids.ids)],
            'context': {'default_batch_id': self.id},
        }

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "New") == "New":
                vals["name"] = self.env["ir.sequence"].next_by_code("lims.batch") or "New"
        return super(LimsBatch, self).create(vals_list)

    def action_set_to_progress(self):
        """Set the batch to 'WIP' state."""
        for batch in self:
            batch.state = 'progress'

    def action_set_to_done(self):
        """Set the batch to 'Done' state, with validation if required."""
        for batch in self:
            if any(analysis.state != 'valid' for analysis in batch.analysis_ids):
                raise UserError("Please insure that all tests are validated before apply this action")
            batch.state = 'done'

    def action_set_to_draft(self):
        """Reset the batch to 'Draft' state."""
        for batch in self:
            batch.state = 'draft'

    def action_set_to_cancel(self):
        """Cancel the batch and set state to 'Cancel'."""
        for batch in self:
            batch.state = 'cancel'

    def create_validated_picking(self):
        """Create a validated stock picking with specific lot numbers from the batch data, including reagents and batch components."""
        Picking = self.env['stock.picking']
        Move = self.env['stock.move']
        MoveLine = self.env['stock.move.line']

        # Specify picking type (e.g., internal, outgoing, incoming)
        picking_type = self.env['stock.picking.type'].search([
            ('sequence_code', '=', 'CONS'),  # Adjust the code to match your specific picking type
            ('company_id', '=', self.env.company.id)  # Ensuring it's for the correct company
        ], limit=1)  # Adjust according to your use case

        # Create the picking
        picking = Picking.create({
            'partner_id': self.company_id.partner_id.id,
            'scheduled_date': self.date,
            'picking_type_id': picking_type.id,
            'origin': self.name,
            'location_id': picking_type.default_location_src_id.id,
            'location_dest_id': picking_type.default_location_dest_id.id,
        })

        self.picking_id = picking.id

        # Collect consumables and reagents with a lot ID into a unified list of dictionaries
        combined_items = []

        # Add consumables to combined_items
        for cons in self.batch_component_ids.filtered(
                lambda c: c.product_id.type == 'consu' and not c.is_consumed and c.type != 'Reagent'):
            cons.is_consumed = True
            combined_items.append({
                'item': cons,
                'product_id': cons.product_id,
                'lot_id': False,
                'quantity': cons.quantity,
                'is_consumed': cons.is_consumed,
            })

        # Add reagents with lot ID to combined_items
        for reagent in self.reagents.filtered(lambda r: r.lot_id and not r.is_consumed):
            reagent.is_consumed = True
            combined_items.append({
                'item': reagent,
                'product_id': reagent.product_id,
                'lot_id': reagent.lot_id,
                'quantity': 1,
                'is_consumed': reagent.is_consumed,
            })

        if not combined_items:
            raise UserError("Please add new reagent or consumable with lot number for this batch.")

        for item in combined_items:
            product_id = item.get('product_id', False)
            if not product_id:
                raise UserError("Each reagent or consumable must have a product specified.")

            # Create the stock move
            move = Move.create({
                'picking_id': picking.id,
                'name': f"{self.name} - {product_id.name}",
                'product_id': product_id.id,
                'product_uom_qty': item.get('quantity', 1),  # Set quantity; adjust as necessary
                'product_uom': product_id.uom_id.id,
                'location_id': picking.location_id.id,
                'location_dest_id': picking.location_dest_id.id,
            })

            # Create move line with lot/serial number if available
            move_line_vals = {
                'move_id': move.id,
                'picking_id': picking.id,
                'product_id': product_id.id,
                'quantity': 1.0,  # Adjust quantity as necessary
                'product_uom_id': product_id.uom_id.id,
                'location_id': picking.location_id.id,
                'location_dest_id': picking.location_dest_id.id,
                'batch_id': self.id
            }
            lot_id = item.get('lot_id', False)
            if lot_id:
                move_line_vals['lot_id'] = lot_id.id  # Assign lot/serial number

            move_line = MoveLine.create(move_line_vals)
            self.moves_ids = [(4, move_line.id)]

        # Confirm and validate the picking
        picking.action_confirm()
        picking.action_assign()
        picking.button_validate()

        return picking

    @api.onchange('reagents')
    def onchange_reagent(self):
        for reagent in self.reagents:
            if reagent.lot_id.expiration_date:
                if reagent.lot_id and reagent.lot_id.expiration_date <= fields.Datetime.now():
                    raise UserError("lot/part number %s is expired" % reagent.lot_id.name)

    @api.onchange('batch_kit_id')
    def _onchange_batch_kit_id(self):
        if self.batch_kit_id:
            # Clear existing components
            self.batch_component_ids = self.operator_ids = self.reagents = [(5, 0, 0)]
            # Copy components from BOM template to the batch
            components = []
            reagents = []
            operators = []
            for component in self.batch_kit_id.kit_line:
                components.append((0, 0, {
                    'type': component.type,
                    'product_id': component.product_id.id,
                    'uom_id': component.uom_id,
                    'quantity': component.quantity,
                    'cost_per_unit': component.cost_per_unit,
                }))
            for reagent in self.batch_kit_id.kit_line.filtered(lambda l: l.type == 'Reagent'):
                for i in range(int(reagent.quantity)):
                    reagents.append((0, 0, {
                        'product_id': reagent.product_id.id,
                    }))

            for operator in self.batch_kit_id.operators:
                operators.append((0, 0, {
                    'operator_id': operator.operator_id.id,
                    'duration': operator.duration
                }))

            self.update({'reagents': reagents,
                         'batch_component_ids': components,
                         'operator_ids': operators
                         })