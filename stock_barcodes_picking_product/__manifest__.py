# Copyright 2019 Sergio Teruel <sergio.teruel@tecnativa.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
{
    "name": "Stock Barcodes Picking Product Manu",
    "summary": "It provides read barcode on stock operations.",
    "version": "12.0.1.0.0",
    "author": "Odoo Community Association (OCA)/Elego Software Solutions GmbH",
    "website": "https://github.com/OCA/stock-logistics-barcode",
    "license": "AGPL-3",
    "category": "Extra Tools",
    "depends": [
        "stock_barcodes",
    ],
    "data": [
        'views/stock_picking_views.xml',
        'wizard/stock_barcodes_read_picking_product_views.xml',
    ],
    "installable": True,
}
