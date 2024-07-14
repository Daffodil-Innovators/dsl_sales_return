from odoo import models, fields, api, _
from odoo.exceptions import UserError


class SalesReturnStage(models.Model):
    _name = 'sales.return.stage'  
    _order = 'sequence asc'
    _description = 'Watch Service Status'

    name = fields.Char(required=True, translate=True)
    is_damage = fields.Boolean(default=False)
    sequence = fields.Integer()
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('name_unique', 'unique(name)', 'Stage already exists!'),
    ]
    