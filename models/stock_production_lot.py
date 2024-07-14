from odoo import models, fields, api, _


class StockProductionLot(models.Model):
    _inherit = 'stock.production.lot'


    is_sales_return = fields.Boolean(string='Is Sales Return', default=False)