# Copyright 2019 Sergio Teruel <sergio.teruel@tecnativa.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import models, api


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def action_barcode_scan_manu(self):
        location = self.location_id
        location_dest = self.location_dest_id
        action = self.env.ref(
            'stock_barcodes_picking_product.action_stock_barcodes_read_picking_product').read()[0]
        action['context'] = {
            'default_location_id': location.id,
            'default_location_dest_id': location_dest.id,
            'default_partner_id': self.partner_id.id,
            'default_picking_id': self.id,
            'default_res_model_id':
                self.env.ref('stock.model_stock_picking').id,
            'default_res_id': self.id,
            'default_picking_type_code': self.picking_type_code,
        }
        return action

    @api.multi
    def do_unreserve(self):
        res = super().do_unreserve()
        self.env['stock.barcodes.read.log'].search([
            ('picking_id', '=', self.ids),
        ]).unlink()
        return res
