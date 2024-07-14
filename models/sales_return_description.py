from odoo import models, fields, api, _


class SalesReturnDescription(models.Model):
    _name = 'sales.return.description'    
    _rec_name = 'repair_description'   

    repair_description = fields.Char(string='Repair Description')