from odoo import models, fields, api, _


class SalesReturnHistory(models.Model):
    _name = 'sales.return.history'    
    _rec_name = 'product' 

    product = fields.Char(string='Product')
    serial = fields.Char(string='Serial')
    qty = fields.Float(string='Quantity')
    purchase_date = fields.Date(string='Purchase Date')
    price_unit = fields.Float(string='Product Price')
    sales_return_id = fields.Many2one('sales.return')
    
   