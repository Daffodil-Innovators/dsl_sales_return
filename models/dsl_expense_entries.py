import time
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from datetime import date, datetime, timedelta

class ExternalEntries(models.Model):
    _inherit = "dsl.expense.entries"
    
    scrap_management_id = fields.Many2one('stock.scrap.management', string="Scrap Management")
    
    