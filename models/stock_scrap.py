from odoo import models, fields, api, _


class StockScrap(models.Model):
    _inherit = 'stock.scrap'


    serial = fields.Char(string='Serial Number', required=False)


    # @api.model
    # def create(self, vals):
    #     vals['serial'] = self.env['ir.sequence'].next_by_code('stock.scrap') or _('New')