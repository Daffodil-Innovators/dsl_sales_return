from odoo import models, fields, api, _
from datetime import datetime, timedelta
from odoo.exceptions import UserError, Warning


class SalesReturnEntries(models.Model):
    _name = 'sales.return.expense.entries'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    
    
    def _get_default_expense_account(self):
        param = self.env['ir.config_parameter'].sudo()
        return self.env['account.account'].sudo().browse(int(param.get_param('dsl_sales_return.sr_expense_account_id'))).id
    

    def _get_default_payment_journal(self):
        param = self.env['ir.config_parameter'].sudo()
        return self.env['account.account'].sudo().browse(int(param.get_param('dsl_sales_return.sr_payment_journal_id'))).id
    

    def _get_default_expense_journal(self):
        param = self.env['ir.config_parameter'].sudo()
        return self.env['account.journal'].sudo().browse(int(param.get_param('dsl_sales_return.sr_expense_journal_id'))).id
    
    
    name = fields.Char('Number', default="Draft")
    memo = fields.Char('Memo')
    entry_date = fields.Date('Date', required=True , default=lambda self: datetime.now())
    expense_account = fields.Many2one('account.account',string='Expense A/C', required=True, default=_get_default_expense_account)
    payment_journal = fields.Many2one('account.journal',string='Payment Journal', required=True, default=_get_default_payment_journal)
    expense_journal = fields.Many2one('account.journal', string='Expense Journal', required=True, default=_get_default_expense_journal)
    cheque = fields.Char('Cheque No.')
    cheque_date = fields.Date('Cheque Date')
    bank = fields.Char('Bank Name')
    amount = fields.Float(string='Payment Amount', store=True, default=0.0)
    company_id =fields.Many2one('res.company', stirng="Company", default=lambda self: self.env.company.id)
    journal_entry_id = fields.Many2many('account.move', string='Journal Entries')
    employee_id = fields.Many2one('hr.employee','Employee')
    is_payment_bank = fields.Char('Is Bank')
    state = fields.Selection(
        [
            ('new', 'New'),
            ('request','On Approval'),
            ('approved', 'Approved'),
            ('done', 'Confirmed'),
        ], 
        string='State',
        default='new',
        track_visibility='onchange',
        required=True,
        copy=False,
    )
    have_employee_wise_expense = fields.Boolean("Add Employee wise Expense", default=False)
    line_ids = fields.One2many('sales.return.expense.entries.line','expense_id','expense line')
    expense_line_ids = fields.One2many('multi.sales.return.expense.entries.line','expense_id','expense line')
    add_multiple = fields.Boolean('Add Multiple')
    branch_id = fields.Many2one('aam.branch', string="Branch", default=lambda self: self.env.user.branch_id.id)
    approver_id = fields.Many2one('res.users', string="Approver")
    scrap_management_id = fields.Many2one('stock.scrap.management', string="Scrap Management")
    product_adj_line_ids = fields.One2many('product.adjustment.line', 'expense_entries_id', string="Product Adjustment Line")
    is_approved = fields.Boolean(string='Is Approved', readonly="1", default=False, compute='_compute_approval_sales_return_expense_entries_user')
    is_validate = fields.Boolean(string='Is Validate', readonly="1", default=False)


    @api.onchange('payment_journal')
    def onchange_payment_journal(self):
        self.is_payment_bank=self.payment_journal.type == 'bank'
    
    
    def _compute_approval_sales_return_expense_entries_user(self):
        for rec in self:
            is_approved = False
            if rec.approval_id.state == 'Submitted':
                for line in rec.approval_id.line_ids:
                    if line.state != 'approve' and line.user_id.id == rec.env.uid:
                        is_approved = True
                        break
                    else:
                        self.is_approved = False
            print("is_approved",is_approved)
            rec.is_approved = is_approved


    @api.onchange('line_ids')
    def onchange_line_ids(self):
        total = 0
        for line in self.line_ids:
            total = total + line.cost      
        self.amount = total


    @api.onchange('add_multiple')
    def onchange_add_multiple(self):
        if self.add_multiple:
            self.expense_line_ids = [(0,0,{'account_id':self.expense_account.id,'cost':self.amount})]

    
    @api.onchange('expense_line_ids')
    def onchange_expense_line_ids(self):
        total = 0
        for line in self.expense_line_ids:
            total = total + line.cost      
        self.amount = total  


    def get_default_journal_value(self):
        return self.company_id.ee_expense_journal_id.id


    @api.model
    def create(self, vals):
        vals['name'] = self.env['ir.sequence'].next_by_code('sales.return.expense.entries')
        res = super(SalesReturnEntries, self).create(vals)
        if res.have_employee_wise_expense:
            total = 0
            for line in res.line_ids:
                total = total + line.cost      
            res.amount = total
        if res.add_multiple:
            total = 0
            for line in res.expense_line_ids:
                total = total + line.cost      
            res.amount = total
        scrap_management = self.env['stock.scrap.management'].search([('id','=',res.scrap_management_id.id)])
        scrap_management.write({'is_expense_entries':True})
        scrap_management.action_validatation()
        return res


    def request_approval_sales_return_entries(self):
        self.state='request'
        self.approver_id = self.branch_id.ee_1st_approver.id
        self.send_mail_to_approver(self.branch_id.ee_1st_approver)
    
    
    def approve_sales_return_expense_entries(self):
        for rec in self:
            rec.approval_id.action_approve()
            if rec.approval_id.state == 'Approved':
                rec.state = 'approved'
                
    
    def validate_sales_return_entries(self):
        self.state='done'
        expense_move_id = self.env['account.move'].create({
            'journal_id': self.expense_journal.id,
            'date': self.entry_date,
            'company_id': self.company_id.id,
            'ref': self.name,
        })
        if not (self.add_multiple and self.expense_line_ids):
            self.env['account.move.line'].with_context(check_move_validity=False).create({
                'name': 'Expense Account',
                'journal_id': self.expense_journal.id,
                'date': self.entry_date,
                'company_id': self.company_id.id,
                'account_id': self.expense_account.id,
                'debit': self.amount,
                'credit': 0.0,
                'move_id': expense_move_id.id,
                'date_maturity': self.entry_date,
            })
        else:
            for line in self.expense_line_ids:
                self.env['account.move.line'].with_context(check_move_validity=False).create({
                    'name': 'Expense Account',
                    'journal_id': self.expense_journal.id,
                    'date': self.entry_date,
                    'company_id': self.company_id.id,
                    'account_id': line.account_id.id,
                    'debit': line.cost,
                    'credit': 0.0,
                    'move_id': expense_move_id.id,
                    'date_maturity': self.entry_date,
                })
        self.env['account.move.line'].with_context(check_move_validity=True).create({
            'name': 'Payble Account',
            'journal_id': self.expense_journal.id,
            'date': self.entry_date,
            'company_id': self.company_id.id,
            'account_id': self.company_id.ee_payable_account_id.id,
            'debit': 0.0,
            'credit': self.amount,
            'move_id': expense_move_id.id,
            'date_maturity': self.entry_date,
        })

        ## New Journal
        for product_adj_line_id in self.product_adj_line_ids:
            print("product_adj_line_id.product_id.categ_id.property_account_expense_categ_id.id-------", product_adj_line_id.product_id.categ_id.property_account_expense_categ_id.id)
            self.env['account.move.line'].with_context(check_move_validity=True).create({
                'name': 'Stock Interim',
                'journal_id': self.expense_journal.id,
                'date': self.entry_date,
                'company_id': self.company_id.id,
                'account_id': product_adj_line_id.product_id.categ_id.property_stock_account_output_categ_id.id,
                'debit': self.amount,
                'credit': 0.0,
                'move_id': expense_move_id.id,
                'date_maturity': self.entry_date,
            })
            print("product_adj_line_id.product_id.categ_id.property_stock_account_output_categ_id.id-------", product_adj_line_id.product_id.categ_id.property_stock_account_output_categ_id.id)
            self.env['account.move.line'].with_context(check_move_validity=True).create({
                'name': 'Account Receivable',
                'journal_id': self.expense_journal.id,
                'date': self.entry_date,
                'company_id': self.company_id.id,
                'account_id': product_adj_line_id.product_id.categ_id.property_account_expense_categ_id.id,
                'debit': 0.0,
                'credit': self.amount,
                'move_id': expense_move_id.id,
                'date_maturity': self.entry_date,
            })
        expense_move_id.action_post()

        payment_move_id = self.env['account.move'].create({
            'journal_id': self.payment_journal.id,
            'date': self.entry_date,
            'company_id': self.company_id.id,
            'ref': self.name,
        })
        self.env['account.move.line'].with_context(check_move_validity=False).create({
            'name': 'Payable Account',
            'journal_id': self.payment_journal.id,
            'date': self.entry_date,
            'company_id': self.company_id.id,
            'account_id': self.company_id.ee_payable_account_id.id,
            'debit': self.amount,
            'credit': 0.0,
            'move_id': payment_move_id.id,
            'date_maturity': self.entry_date,
        })
        self.env['account.move.line'].with_context(check_move_validity=True).create({
            'name': 'Payment',
            'journal_id': self.payment_journal.id,
            'date': self.entry_date,
            'company_id': self.company_id.id,
            'account_id': self.payment_journal.default_account_id.id,
            'debit': 0.0,
            'credit': self.amount,
            'move_id': payment_move_id.id,
            'date_maturity': self.entry_date,
        })
        payment_move_id.action_post()
        
        self.journal_entry_id = [(4,expense_move_id.id),((4,payment_move_id.id))]

    
    def action_journal_entries(self):
        return{
            'name': _('Journal Entries'),
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'res_model': 'account.move',
            'domain': [('id', 'in', self.journal_entry_id.ids)]
        }


    def send_mail_to_approver(self, approver):
        web_base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        body = "<p>Dear %s<br/>You are requested to approve this expense.<br/><br/><a style='background-color:#875A7B;padding:8px 16px 8px 16px; text-decoration:none; color:#fff; border-radius:5px' href='%s/mail/view?model=sales.return.expense.entries&amp;res_id=%s' data-oe-model='sales.return.expense.entries' data-oe-id='%s'>View Expenses</a></p>" % (approver.name, web_base_url, self.id, self.id,)
        values = {
                    'subject': "[ "+self.company_id.name +"] Expenses approve requests.",
                    'body_html': body,
                    'record_name': "[ "+self.company_id.name +"] Expenses approve requests.",
                    'email_from': self.env.user.email_formatted,
                    'reply_to': self.env.user.email_formatted,
                    'model': 'sales.return.expense.entries',
                    'res_id': self.id,
                    'message_type': 'email',
                    'recipient_ids': [(6,0,[approver.partner_id.id])]
                }
        message = self.env['mail.mail'].sudo().create(values)
        message.send()


    def action_validate_adjustment(self):
        inventory = self.env['stock.inventory'].create({
            'name': 'Production Adjustment - ' + str(self.entry_date),
            'branch_id': self.branch_id.id,
            'location_ids': [(6,0,self.branch_id.location_id.ids)],
        })
        for item in self.product_adj_line_ids:
            existing_line = self.env['stock.inventory.line'].search([('inventory_id','=',inventory.id),('product_id','=',item.product_id.id),('prod_lot_id','=',item.prod_lot_id.id)])
            if existing_line:
                existing_line.product_qty = existing_line.product_qty - item.quantity
            else:
                theoretical_qty = item.product_id.get_theoretical_quantity(
                    item.product_id.id, 
                    self.branch_id.location_id.id, 
                    lot_id=item.prod_lot_id.id, 
                    package_id=False, 
                    owner_id=False, 
                    to_uom=item.product_id.uom_id.id)
                print('item.prod_lot_id.id', item.prod_lot_id.id)
                print('item.quantity', item.quantity)
                new_qty = theoretical_qty - item.quantity
                print("theoretical_qty",theoretical_qty)
                print("new_qty",new_qty)
                self.env['stock.inventory.line'].create({
                    'product_id': item.product_id.id,
                    'product_uom_id': item.product_id.uom_id.id,
                    'product_qty': new_qty,
                    'location_id': self.branch_id.location_id.id,
                    'prod_lot_id': item.prod_lot_id.id,
                    'inventory_id': inventory.id,
                })

        try:
            inventory.action_start()
            inventory.action_validate()
            self.is_validate = True

        except Exception as e:
            raise UserError(_(e))


class Expense_EntriesLine(models.Model):
    _name = 'sales.return.expense.entries.line'

    employee_id = fields.Many2one('hr.employee','Employee Name')
    cost = fields.Float('Cost')
    expense_id = fields.Many2one('sales.return.expense.entries','Expense Entry')


class MultiEntriesLine(models.Model):
    _name = 'multi.sales.return.expense.entries.line'

    account_id = fields.Many2one('account.account','Accounts', domain="[('user_type_id.name','=','Expenses')]")
    cost = fields.Float('Cost')
    expense_id = fields.Many2one('sales.return.expense.entries','Expense Entry')


class ProductionAdjustmentLine(models.Model):
    _name = "product.adjustment.line"
    
    expense_entries_id = fields.Many2one('sales.return.expense.entries','Expense Entry')
    product_id = fields.Many2one("product.product", string="Product")
    quantity = fields.Float("Quantity", digits='Product Unit of Measure')
    unit_cost = fields.Float(string="Unit Cost", compute='_compute_unit_cost')
    production_adjustment_id = fields.Many2one('inventory.production.adjustment', string="Transfer")
    prod_lot_id = fields.Many2one('stock.production.lot', string="Lot/Serial")
    prod_lot_name = fields.Char(string="Lot/Serial")
    
    
    @api.depends('quantity')
    def _compute_unit_cost(self):
        for rec in self:
            rec.unit_cost = rec.product_id.lst_price * rec.quantity


    @api.onchange('product_id')
    def _onchange_product_id(self):
        for rec in self:
            lot_list = []
            lot_ids = self.env['stock.production.lot'].search([('product_id','=',rec.product_id.id), ('is_sales_return', '=', False)])
            if lot_ids:
                for lot in lot_ids:
                    lot_list.append(lot.id)
                return {'domain': {'prod_lot_id': [('id', 'in', lot_list)]}}
            
            
