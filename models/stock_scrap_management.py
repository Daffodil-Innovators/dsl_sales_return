from odoo import models, fields, api, _


class StockScrapManagement(models.Model):
    _inherit = 'stock.scrap.management'

    sales_return_id = fields.Many2one('sales.return', string='Sales Return')
    branch_id = fields.Many2one('aam.branch', string='Branch')
    expense_count = fields.Integer(compute='_expense_count', string='# Advance',copy=False)
    is_expense_entries = fields.Boolean(string='Is Expense Entries', default=False)
    
    
    def _expense_count(self):
        for rec in self:
            payment_ids = self.env['sales.return.expense.entries'].search([('scrap_management_id', '=', rec.id)])
            rec.expense_count = len(payment_ids)
    
    
    def action_view_expense_entries(self):
        scraps = self.env['sales.return.expense.entries'].search([('scrap_management_id', '=', self.id)])
        if scraps:
            action = {
                'name': 'Scrap',                                  
                'type': 'ir.actions.act_window',
                'view_mode': 'tree,form',
                'res_model': 'sales.return.expense.entries',
                'views': [(False, 'tree'), (False, 'form')],
                'domain': [('id', 'in', scraps.ids)],
                'context': {'create': False}
            }
        else:
            action = {'type': 'ir.actions.act_window_close'}
        return action 
    
    
    def action_confirm(self):
        res = super(StockScrapManagement, self).action_confirm()
        if self.sales_return_id:
            print('self.sales_return_id', self.sales_return_id)
            self.sales_return_id.is_scrap = True
        return res        

    
    def action_expense_entries(self):
        action = {
            'name': _('Sales Return Expense Entries'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': self.env.ref('dsl_sales_return.sales_return_expense_entries_form_view').id,
            'res_model': 'object',
            'res_model': 'sales.return.expense.entries',
            'target': 'new',
            'context': {
                'default_scrap_management_id': self.id,
                'default_branch_id': self.env.context.get('branch_id', False),
                'default_company_id': self.company_id.id,
                'default_branch_id': self.branch_id.id,
            }
        }
        return action

