# Copyright 2019 Sergio Teruel <sergio.teruel@tecnativa.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import _, fields, models
from odoo.fields import first
from odoo.addons import decimal_precision as dp
from odoo.exceptions import ValidationError
from odoo.tools.float_utils import float_compare, float_is_zero


class WizStockBarcodesReadPickingProduct(models.TransientModel):
    _name = 'wiz.stock.barcodes.read.picking.product'
    _inherit = 'wiz.stock.barcodes.read'
    _description = 'Wizard to read barcode on picking for product'

    picking_id = fields.Many2one(
        comodel_name='stock.picking',
        readonly=True,
    )
    picking_type_code = fields.Selection([
        ('incoming', 'Vendors'),
        ('outgoing', 'Customers'),
        ('internal', 'Internal'),
    ], 'Type of Operation')
    location_dest_id = fields.Many2one(
        string='To',
        comodel_name='stock.location',
        #related='picking_id.location_dest_id',
    )
    picking_product_qty = fields.Float(
        string='Picking Product quantities',
        digits=dp.get_precision('Product Unit of Measure'),
        readonly=True,
    )

    def name_get(self):
        return [
            (rec.id, '{} - {} - {}'.format(
                _('Barcode reader'),
                rec.picking_id.name, self.env.user.name)) for rec in self]

    def _prepare_move(self):
        return {
            'name': self.product_id.name,
            'product_id': self.product_id.id,
            'location_id': self.location_id.id,
            'location_dest_id': self.location_dest_id.id,
            'product_uom': self.product_id.uom_id.id,
            'product_uom_qty': self.product_qty,
            'picking_id': self.picking_id.id,
        }

    def _prepare_move_domain(self):
        """
        Use the same domain for create or update a stock move line.
        Source data is scanning log record if undo or wizard model if create or
        update one
        """
        return [
            ('picking_id', '=', self.picking_id.id),
            ('product_id', '=', self.product_id.id),
            ('location_id', '=', self.location_id.id),
            ('location_dest_id', '=', self.location_dest_id.id),
        ]

    def _prepare_move_line(self, move):
        return {
            'picking_id': self.picking_id.id,
            'move_id': move.id,
            'product_id': self.product_id.id,
            'location_id': self.location_id.id,
            'location_dest_id': self.location_dest_id.id,
            'product_uom_id': self.product_id.uom_id.id,
            'product_uom_qty': self.product_qty,
            'qty_done': self.product_qty,
            'lot_id': self.lot_id.id,
        }

    def _prepare_move_line_domain(self, log_scan=False):
        """
        Use the same domain for create or update a stock move line.
        Source data is scanning log record if undo or wizard model if create or
        update one
        """
        record = log_scan or self
        return [
            ('picking_id', '=', self.picking_id.id),
            ('product_id', '=', record.product_id.id),
            ('location_id', '=', record.location_id.id),
            ('lot_id', '=', record.lot_id.id),
        ]

    def _add_move_line(self):
        StockQuant = self.env['stock.quant']
        StockMove = self.env['stock.move']
        StockMoveLine = self.env['stock.move.line']
        line = StockMoveLine.search(
            self._prepare_move_line_domain(), limit=1)
        if line:
            line.write({
                'product_uom_qty': line.product_uom_qty + self.product_qty,
                'qty_done': line.qty_done + self.product_qty,
            })
            line.move_id.write({'product_uom_qty': line.product_uom_qty})
        else:
            move = StockMove.search(
                self._prepare_move_domain(), limit=1)
            if not move:
                move = StockMove.create(self._prepare_move())
            line = StockMoveLine.create(self._prepare_move_line(move))
        line.move_id.state = "assigned"
        self.picking_product_qty = line.product_uom_qty

    def check_done_conditions(self):
        StockQuant = self.env['stock.quant']
        if self.product_id.tracking != 'none' and not self.lot_id:
            self._set_messagge_info('info', _('Waiting for input lot'))
            return False
        if self.picking_type_code in ['outgoing', 'internal']:
            avail_qty = StockQuant._get_available_quantity(
                self.product_id, self.location_id, lot_id=self.lot_id
            )
            if float_compare(self.product_qty, avail_qty, precision_rounding=self.product_id.uom_id.rounding) > 0:
                self._set_messagge_info('info', _('No found enough quantity'))
                return False
        return super().check_done_conditions()

    def action_done(self):
        result = super().action_done()
        if result:
            #if self.picking_type_code == 'incoming':
            #    self._update_incoming_move()
            #if self.picking_type_code in ['outgoing', 'internal']:
            self._add_move_line()
        return result

    def action_manual_entry(self):
        result = super().action_manual_entry()
        if result:
            self.action_done()
        return result

    def reset_qty(self):
        super().reset_qty()
        self.picking_product_qty = 0.0

    def action_undo_last_scan(self):
        StockQuant = self.env['stock.quant']
        res = super().action_undo_last_scan()
        log_scan = first(self.scan_log_ids.filtered(
            lambda x: x.create_uid == self.env.user))
        if log_scan:
            move_line = self.env['stock.move.line'].search(
                self._prepare_move_line_domain(log_scan=log_scan))
            if move_line.picking_id.state == 'done':
                raise ValidationError(_(
                    'You can not remove a scanning log from an picking '
                    'validated')
                )
            if move_line:
                qty = move_line.product_uom_qty - log_scan.product_qty
                move_line.write({
                    'product_uom_qty': max(qty, 0.0),
                    'qty_done': max(qty, 0.0),
                })
                move_line.move_id.product_uom_qty = max(qty, 0.0)
                self.picking_product_qty = move_line.product_uom_qty
                #if float_is_zero(move_line.product_uom_qty, precision_rounding=self.product_id.uom_id.rounding):
                #    move_line.unlink()
        log_scan.unlink()
        return res
