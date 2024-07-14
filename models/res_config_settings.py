# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'
    
    sr_expense_account_id = fields.Many2one('account.account', string="Expense Account", config_parameter='dsl_sales_return.sr_expense_account_id')
    sr_payable_account_id = fields.Many2one('account.account', string="Payable Account", config_parameter='dsl_sales_return.sr_payable_account_id')
    sr_payment_journal_id = fields.Many2one('account.journal', string="Payment Journal", config_parameter='dsl_sales_return.sr_payment_journal_id')
    sr_expense_journal_id = fields.Many2one('account.journal', string="Expense Journal", config_parameter='dsl_sales_return.sr_expense_journal_id')

