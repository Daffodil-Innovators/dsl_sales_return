from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta


class SaleOrder(models.Model):
    _inherit = 'sale.order.line'


    warranty = fields.Integer(related='product_id.warranty',string="Warranty")
    warranty_type = fields.Selection(related='product_id.warranty_type',string='Product Duration')
    expiry_date = fields.Date(string="Expiry Date", compute="_compute_expiry_date")


    @api.depends('warranty', 'warranty_type')
    def _compute_expiry_date(self):
        for product in self:
            if product.warranty and product.warranty_type == 'day':
                expiry_delta = timedelta(days=product.warranty)
            elif product.warranty and product.warranty_type == 'week':
                expiry_delta = timedelta(weeks=product.warranty)
            elif product.warranty and product.warranty_type == 'month':
                expiry_delta = timedelta(days=30 * product.warranty)  
            elif product.warranty and product.warranty_type == 'year':
                expiry_delta = timedelta(days=365 * product.warranty) 
            else:
                expiry_delta = timedelta()  

            product.expiry_date = self.order_id.date_order + expiry_delta


    
    def name_get(self):
        res = []
        for line in self:
            product = line.product_id.name
            order = line.order_id.name
            name = order + ' / ' + product
            res.append((line.id, name))
        return res