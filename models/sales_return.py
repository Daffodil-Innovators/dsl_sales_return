from datetime import datetime
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import pytz
import random
import string


import logging

_logger = logging.getLogger(__name__)


class SalesReturn(models.Model):
    _name = 'sales.return'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Service Center"
    
    
    def _get_default_state(self):
        stage_ids = self.env['sales.return.stage'].search([('active', '=', True)],order='sequence asc', limit=1).ids
        if stage_ids:
            return stage_ids[0]
        else:
            return False
        
        
    @api.model
    def _default_picking_transfer(self):
        """To get the default picking transfers"""
        type_obj = self.env['stock.picking.type']
        company_id = self.env.context.get('company_id') or self.env.user.company_id.id
        types = type_obj.search([('code', '=', 'outgoing'), ('warehouse_id.company_id', '=', company_id)], limit=1)
        if not types:
            types = type_obj.search( [('code', '=', 'outgoing'), ('warehouse_id', '=', False)])
        return types[:4]
    

    # Customer Info
    name = fields.Char(string='Service Number', copy=False, default="New")
    partner_id = fields.Many2one('res.partner', string="Customer Name")
    access_code = fields.Char(string="Access Code", readonly=True)
    contact_no = fields.Char(related='partner_id.phone', string="Contact Number")
    email_id = fields.Char(related='partner_id.email', string="Email")
    number = fields.Char(string='Service Id')
    street = fields.Char(related='partner_id.street', string="Address")
    street2 = fields.Char(related='partner_id.street2', string="Address")
    city = fields.Char(related='partner_id.city', string="Address")
    state_id = fields.Many2one(related='partner_id.state_id', string="Address")
    zip = fields.Char(related='partner_id.zip', string="Address")
    country_id = fields.Many2one(related='partner_id.country_id', string="Address") 
    user_id = fields.Many2one('res.users', string='User', default=lambda self: self.env.user.id)
    delivery_location_id=fields.Many2one('delivery.location',string="Delivery Location")
    receive_location_id=fields.Many2one('delivery.location',string="Receive Location")
    # receive_quantity = fields.Integer(string="Received Quantity")
    receive_by = fields.Many2one('res.users', string="Receive By")

    # Product Info
    product_id = fields.Many2one('product.template', string="Product to Repair")
    sale_order_line_id = fields.Many2one('sale.order.line')
    description_ids = fields.Many2many('sales.return.description', string="Repair Description")
    watch_price = fields.Float(related='product_id.list_price',string='Price')
    prod_lot_id = fields.Many2one('stock.production.lot', string="Lot/Serial")
    order_qty = fields.Float(related='sale_order_line_id.order_qty',string="Ordered")
    return_qty = fields.Float(string="Returned", default="0.0", store=True)
    warranty = fields.Integer(related='sale_order_line_id.warranty',string="Warranty")
    warranty_remain = fields.Integer(string="Warranty Remain")
    expiry_date=fields.Date(related='sale_order_line_id.expiry_date',string="Expiry Date")
    warranty_duration = fields.Selection(related='sale_order_line_id.warranty_type',string='Product Duration')
    # warranty_duration = fields.Char(related='product_id.warranty_type',string='Product Duration')
    service_watch_policy = fields.Html(related='product_id.watch_policy',string='Policy')
    image_1920 = fields.Binary(string='image', store=True, attachment=True)
    warranty_number = fields.Char(string="Warranty No ", help="warranty details")
    watch_no = fields.Char(string="Product Ref No")
    date_request = fields.Date(string="Requested date", default=fields.Date.context_today)
    return_date = fields.Date(string="Delivery Date")
    technician_name = fields.Many2one('res.users', string="Technician")
    diagnosis_by = fields.Many2one('res.users', string="Diagnosis By") 
    service_state = fields.Selection(
        [
            ('draft', 'Draft'), 
            ('assigned', 'Assigned'),
            ('returned', 'Returned'),
            ('not_solved', 'Not solved'),
            ('completed', 'Completed'),
        ],
        string='Service Status', 
        default='draft', 
        track_visibility='always',
    )
    
    complain_tree = fields.One2many('sales.return.complain.tree', 'complaint_id', string='complain Tree')
    complain_ids = fields.One2many('sales.return.complain', 'sales_return_id', string='complain Tree')
    # product_order_line = fields.One2many('product.order.line', 'product_order_id', string='Parts Order Lines')

    internal_notes = fields.Text(string="Remarks")
    invoice_count = fields.Integer(compute='_invoice_count', string='# Invoice',copy=False)
    move_ids = fields.Many2many("account.move", string='Invoices', compute="_get_invoiced", readonly=True, copy=False)
    first_payment_inv = fields.Many2one('account.move', copy=False)
    first_invoice_created = fields.Boolean(string="First Invoice Created", invisible=True, copy=False)
    journal_type = fields.Many2one('account.journal', 'Journal', invisible=True, default=lambda self: self.env['account.journal'].search([('code', '=', 'SERV')]))
    # company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env['res.company']._company_default_get('sales.return'))
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    product_sale_history_line =fields.One2many('sales.return.history','sales_return_id',string="History Line")                                 
    internal_notes = fields.Html('Internal Notes')
    quotation_notes = fields.Html('Quotation Notes')                              
    state = fields.Selection(
        [
            ('draft', 'Draft'),
            ('receive', 'Product Receive'),
            ('transfer', 'Wirehouse Transfer'),
            ('deliver', 'Ready to Deliver'),
            ('shipped', 'Shipped'),
            ('scrap', 'Damage/Scrap'),
            ('cancel', 'Cancelled'),
        ],
        string='Status',
        copy=False,
        group_expand='_expand_groups',
        default='draft', 
        readonly=True,
        tracking=True,
    )
    move_id = fields.Many2one('account.move', 'Invoice', copy=False, readonly=True, tracking=True, domain=[('move_type', '=', 'out_invoice')])
    stage_id = fields.Many2one('sales.return.stage', 'State', default=_get_default_state, group_expand='_read_group_stage_ids', tracking=True, help='Current state of the Product Service', ondelete="set null")
    # stock_picking_id = fields.Many2one('stock.picking', string="Picking Id")
    # picking_transfer_id = fields.Many2one('stock.picking.type', 'Deliver To', required=True, default=_default_picking_transfer, help="This will determine picking type of outgoing shipment")
    registration_date = fields.Datetime(string='Registration Date')
    color = fields.Integer(string="Color")
    picking_count = fields.Integer(string="Count")
    inventory_id = fields.Many2one('stock.inventory', string="Inventory Adjustment")
    unit_cost = fields.Float(string="Unit Cost", default=0.0)
    scrap_management_id = fields.Many2one('stock.scrap.management', string="Scrap Management")
    scrap_count = fields.Integer(compute='_scrap_count', string='# Advance',copy=False)
    is_in_warranty = fields.Boolean('In Warranty', default=False, help="Specify if the product is in warranty.")
    re_repair = fields.Boolean('Re-repair', default=False, help="Re-repairing.")
    is_approved = fields.Boolean(string='Is Approved', readonly="1", default=False, compute='_compute_watch_approval_user')
    is_scrap = fields.Boolean(string='Is Scrap', readonly="1", default=False)
    product_condition = fields.Selection(
        [
            ('repairable', 'Repairable'),
            ('non_repairable', 'Not Repairable'),
        ],
        string='Product Condition',
        tracking=True, 
        default="repairable", 
    )

        
    @api.onchange('partner_id')
    def get_invoice_info(self):
        if self.partner_id:
            # Clear the existing history lines
            self.product_sale_history_line = [(5, 0, 0)]
            invoice_records = self.env['sale.order'].search([
                ('partner_id', '=', self.partner_id.id),
                ('state', '=', 'sale')
            ])
            history_lines = []
            for record in invoice_records:
                for line in record.order_line:
                    history_lines.append((0, 0, {
                        'product': line.product_id.name,
                        'purchase_date': record.date_order,
                        'price_unit': line.price_unit,
                        'sales_return_id': line.id,
                    }))
            self.product_sale_history_line = history_lines


    @api.onchange('partner_id')
    def onchange_partner_id(self):
        item = []
        sale_orders = self.env['sale.order'].sudo().search([('partner_id', '=', self.partner_id.id)], order='id desc')
        for sale_order in sale_orders:
            for line in sale_order.order_line:
                item.append(line.id)
        print("item", item)
        return {'domain': {'sale_order_line_id': [('id', 'in', item)]}}
    

    @api.onchange('expiry_date')
    def _onchange_expiry_date(self):
        for rec in self:
            if rec.expiry_date != False:
                today_date = datetime.now().date()
                print('today_date', today_date)
                print('rec.expiry_date', rec.expiry_date)
                warranty_remain = rec.expiry_date - today_date
                # rec.warranty_remain = rec.expiry_date - today_date
                print(warranty_remain.days)
                rec.warranty_remain = warranty_remain.days
                if rec.expiry_date < today_date :
                    rec.is_in_warranty = False
                else:
                    rec.is_in_warranty = True
    
    
    @api.onchange('return_qty')
    def _onchange_order_qty(self):
        for rec in self:
            if rec.return_qty > rec.order_qty:
                rec.return_qty = 0.0
                # Use a warning instead of raising an error to allow the change to take effect
                return {
                    'warning': {
                        'title': "Warning!",
                        'message': "Return quantity should be less than ordered quantity",
                    }
                }
    
    
    def _read_group_stage_ids(self, stages, domain, order):
        stage_ids = self.env['sales.return.stage'].search([])
        return stage_ids
    
   
    def _compute_watch_approval_user(self):
        for rec in self:
            is_approved = False
            if rec.approval_id.state == 'Submitted':
                for line in rec.approval_id.line_ids:
                    if line.state != 'Approved' and line.user_id.id == rec.env.uid:
                        is_approved = True
                        break
                    else:
                        self.is_approved = False
            rec.is_approved = is_approved
   

    @api.onchange('return_date')
    def check_date(self):
        """Check the return date and request date"""
        if self.return_date != False:
            return_date_string = datetime.strptime(str(self.return_date),
                                                   "%Y-%m-%d")
            request_date_string = datetime.strptime(str(self.date_request),
                                                    "%Y-%m-%d")
            if return_date_string < request_date_string:
                raise UserError(
                    "Return date should be greater than requested date")
    

    def _generate_access_code(self):
        # Generate a random string for the access code
        access_code_length = 8
        characters = string.ascii_uppercase + string.digits
        return ''.join(random.choice(characters) for i in range(access_code_length))
    
    
    @api.model
    def _expand_groups(self, states, domain, order):
        return ['draft', 'receive', 'transfer', 'deliver', 'shipped', 'scrap', 'cancel']
    
    
    def _scrap_count(self):
        for rec in self:
            payment_ids = self.env['stock.scrap.management'].search([('sales_return_id', '=', rec.id)])
            rec.scrap_count = len(payment_ids)
    
    
    @api.model
    def create(self, vals):
        # """Creating sequence"""
        if 'access_code' not in vals:
            vals['access_code'] = self._generate_access_code()
        if 'company_id' in vals:
            vals['name'] = self.env['ir.sequence'].with_context(force_company=self.env.user.company_id.id).next_by_code('sales.return') or _('New')
        else:
            vals['name'] = self.env['ir.sequence'].next_by_code('sales.return') or _('New')
        # vals['state'] = 'receive'
        if vals['return_qty'] == 0.0:
            raise UserError("Return quantity should be greater than zero")
        return super(SalesReturn, self).create(vals) 
       

    def unlink(self):
        """Supering the unlink function"""
        for i in self:
            if i.state != 'draft':
                raise UserError(
                    _('You cannot delete an assigned service request'))
        return super(SalesReturn, self).unlink()
    
    
    def action_view_scrap(self):
        scraps = self.env['stock.scrap.management'].search([('sales_return_id', '=', self.id)])
        if scraps:
            action = {
                'name': 'Scrap',                                  
                'type': 'ir.actions.act_window',
                'view_mode': 'tree,form',
                'res_model': 'stock.scrap.management',
                'views': [(False, 'tree'), (False, 'form')],
                'domain': [('id', 'in', scraps.ids)],
                'context': {'create': False}
            }
        else:
            action = {'type': 'ir.actions.act_window_close'}
        return action 


    def complete(self):
        for rec in self:
            rec.approval_id.action_approve()
            if rec.approval_id.state == 'Approved':
                rec.state = 'completed'
                rec.registration_date = datetime.now()
    
    
    def action_send_to_wearhouse(self):
        ## Stock In Product.
        inventory = self.env['stock.inventory'].create({
            'name': 'Sales Return Adjustment - ' + str(self.date_request),
            'branch_id': self.partner_id.branch_id.id,
            'location_ids': [(6, 0, self.partner_id.branch_id.location_id.ids)],
        })

        last_lot_name = self.env['stock.production.lot'].sudo().search([('name', 'like', 'SR-%')], order='id desc', limit=1)
        print("last_lot_name", last_lot_name)
        code = "00001"
        if last_lot_name:
            code = str(int(last_lot_name.name.split('-')[-1]) + 1).zfill(5)
        print("self.return_qty", self.return_qty)
        prod_lot_id = self.env['stock.production.lot'].sudo().create({
            'name' : f"SR-{code}",
            'product_id': self.sale_order_line_id.product_id.id,
            'company_id': self.env.company.id,
            'unit_cost': self.sale_order_line_id.price_unit,
            'is_sales_return': True,
        })
        self.prod_lot_id = prod_lot_id.id

        theoretical_qty = self.sale_order_line_id.product_id.get_theoretical_quantity(
            self.sale_order_line_id.product_id.id,
            self.env.user.branch_id.location_id.id,
            lot_id=self.prod_lot_id.id,
            package_id=False,
            owner_id=False,
            to_uom=self.sale_order_line_id.product_id.uom_id.id,
        )
        new_qty = theoretical_qty + self.return_qty
        self.env['stock.inventory.line'].create({
            'product_id': self.sale_order_line_id.product_id.id,
            'product_uom_id': self.sale_order_line_id.product_id.uom_id.id,
            'product_qty': new_qty,
            'location_id': self.env.user.branch_id.location_id.id,
            'prod_lot_id': self.prod_lot_id.id,
            'unit_cost': self.sale_order_line_id.price_unit,
            'inventory_id': inventory.id,
            })

        try:
            inventory.action_start()
            inventory.action_validate()
        except Exception as e:
            raise UserError(_(e))
        
        if self.product_condition == "repairable":
            self.state = 'transfer'
        else:
            self.state = 'scrap'


    def action_ready_to_deliver(self):
        ## Stock Out Product.
        inventory = self.env['stock.inventory'].create({
            'name': 'Production Adjustment - ' + str(self.date_request),
            'branch_id': self.partner_id.branch_id.id,
            'location_ids': [(6, 0, self.partner_id.branch_id.location_id.ids)],
        })
        existing_line = self.env['stock.inventory.line'].search([('inventory_id','=',inventory.id),('product_id','=',self.sale_order_line_id.product_id.id),('prod_lot_id','=',self.prod_lot_id.id)])
        if existing_line:
            print("existing_line", existing_line)
            existing_line.product_qty = existing_line.product_qty - self.picking_count
        else:
            print("ELSE")
            theoretical_qty = self.sale_order_line_id.product_id.get_theoretical_quantity(
                self.sale_order_line_id.product_id.id,
                self.env.user.branch_id.location_id.id,
                lot_id=self.prod_lot_id.id,
                package_id=False,
                owner_id=False,
                to_uom=self.sale_order_line_id.product_id.uom_id.id,
            )
            new_qty = theoretical_qty - self.return_qty
            self.env['stock.inventory.line'].create({
                'product_id': self.sale_order_line_id.product_id.id,
                'product_uom_id': self.sale_order_line_id.product_id.uom_id.id,
                'product_qty': new_qty,
                'location_id': self.env.user.branch_id.location_id.id,
                'prod_lot_id': self.prod_lot_id.id,
                'unit_cost': self.sale_order_line_id.price_unit,
                'inventory_id': inventory.id,
            })
        try:
            inventory.action_start()
            inventory.action_validate()
        except Exception as e:
            raise UserError(_(e))
        
        self.state = 'deliver'
        return True
    

    def action_shipped(self):
        self.state = 'shipped'
    
    
    def action_to_make_scrap_expense_entires(self):
        action = {
            'name': _('Send to Scrap'),
            'view_mode': 'form',
            'view_id': self.env.ref('dsl_sales_return.stock_scrap_management_wizard_form_view').id,
            'res_model': 'stock.scrap.management',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': {
                    'default_sales_return_id': self.id,
					'default_reference': self.prod_lot_id.name,
                    'default_responsible_id': self.env.user.id,
                    'default_company_id': self.company_id.id,
                    'default_branch_id': self.partner_id.branch_id.id,
					'default_item_lines_ids': [(0, 0, {
						'product_id': self.sale_order_line_id.product_id.id,
                        'lot_id': self.prod_lot_id.id,
                        'product_uom_id': self.sale_order_line_id.product_id.uom_id.id,
						'scrap_qty': self.return_qty,
					})],
				},
        }
        return action
    

    # def action_repair_end(self):
    #     if self.filtered(lambda repair: repair.state != 'approved'):
    #         raise UserError(_("Repair must be under repair in order to end reparation."))
    #     for repair in self:
    #         if repair.is_in_warranty == False:
    #             vals = {'state': 'done'}
    #             if not repair.move_id and repair.invoice_method == 'after_repair':
    #                 repair.state = '2binvoiced'
    #         else:
    #             repair.state = 'done'

            
    #         if self.re_repair == True:
    #             ## Stock Out Product.
    #             inventory = self.env['stock.inventory'].create({
    #                 'name': 'Production Adjustment - ' + str(self.date_request),
    #                 'branch_id': self.partner_id.branch_id.id,
    #                 'location_ids': [(6, 0, self.partner_id.branch_id.location_id.ids)],
    #             })
    #             existing_line = self.env['stock.inventory.line'].search([('inventory_id','=',inventory.id),('product_id','=',self.sale_order_line_id.product_id.id),('prod_lot_id','=',self.prod_lot_id.id)])
    #             if existing_line:
    #                 print("existing_line", existing_line)
    #                 existing_line.product_qty = existing_line.product_qty - self.picking_count
    #             else:
    #                 print("ELSE")
    #                 theoretical_qty = self.sale_order_line_id.product_id.get_theoretical_quantity(
    #                     self.sale_order_line_id.product_id.id,
    #                     self.partner_id.branch_id.location_id.id,
    #                     lot_id = self.prod_lot_id.id,
    #                     package_id = False,
    #                     owner_id = False,
    #                     to_uom = self.sale_order_line_id.product_id.uom_id.id,
    #                 )
    #                 new_qty = theoretical_qty - self.picking_count
    #                 self.env['stock.inventory.line'].create({
    #                     'product_id': self.sale_order_line_id.product_id.id,
    #                     'product_uom_id': self.sale_order_line_id.product_id.uom_id.id,
    #                     'product_qty': new_qty,
    #                     'location_id': self.partner_id.branch_id.location_id.id,
    #                     'prod_lot_id': self.prod_lot_id.id,
    #                     'inventory_id': inventory.id,
    #                 })
    #                 try:
    #                     inventory.action_start()
    #                     inventory.action_validate()
    #                 except Exception as e:
    #                     raise UserError(_(e))
    #             return True
    #         # else:
    #         #     action = {
    #         #         'name': _('Expense Entries'),
    #         #         'type': 'ir.actions.act_window',
    #         #         'view_type': 'form',
    #         #         'view_mode': 'form',
    #         #         'view_id': self.env.ref('dsl_product_warranty_registration.inventory_product_not_receive_expense_entries_form_view').id,
    #         #         'res_model': 'object',
    #         #         'res_model': 'dsl.expense.entries',
    #         #         'target': 'new',
    #         #         'context': {
    #         #             'product_not_receive_id': self.id,
    #         #             'default_branch_id': self.branch_id.id,
    #         #             'default_company_id': self.env.context.get('company_id'),
    #         #         }
    #         #     }
    #         #     return action  
  
  
    # def action_repair_cancel_draft(self):
    #     if self.filtered(lambda repair: repair.state != 'cancel'):
    #         raise UserError(_("Repair must be canceled in order to reset it to draft."))
    #     self.write({'state': 'draft'})
    #     return self.write({'state': 'draft'})


    # def action_repair_cancel(self):
    #     if any(repair.state == 'done' for repair in self):
    #         raise UserError(_("You cannot cancel a completed repair order."))
    #     invoice_to_cancel = self.filtered(lambda repair: repair.move_id.state == 'draft').move_id
    #     if invoice_to_cancel:
    #         invoice_to_cancel.button_cancel()
    #     self.write({'state': 'cancel'})
    #     return self.write({'state': 'cancel'})

    
    def action_repair_cancel(self):
        if any(repair.state == 'deliver' for repair in self):
            raise UserError(_("You cannot cancel a Ready to Deliver product."))
        return self.write({'state': 'cancel'})

 
    def action_send_mail(self):
        '''
        This function opens a window to compose an email, with the edi sale template message loaded by default
        '''
        self.ensure_one()
        ir_model_data = self.env['ir.model.data']
        try:
            template_id = ir_model_data.xmlid_to_res_id('dsl_service_shop.email_template_sales_return')
        except ValueError:
            template_id = False
        try:
            compose_form_id = ir_model_data.xmlid_to_res_id('mail.email_compose_message_wizard_form')
        except ValueError:
            compose_form_id = False
        ctx = {
            'default_model': 'sales.return',
            'default_res_id': self.ids[0],
            'default_use_template': bool(template_id),
            'default_template_id': template_id,
            'default_composition_mode': 'comment',
            'default_user_id': self.env.user.id,
        }
        return {
            'name': _('Compose Email'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form_id, 'form')],
            'view_id': compose_form_id,
            'target': 'new',
            'context': ctx,
        }
    
    
    def send_confirmation_email(self):
        '''
        This function opens a window to compose an email, with the service tracker link added in the template
        '''
        self.ensure_one()
        ir_model_data = self.env['ir.model.data']
        try:
            template_id = ir_model_data.xmlid_to_res_id(
                'dsl_service_shop.sales_return_tracker_template')  # Updated the template ID
        except ValueError:
            template_id = False
        try:
            compose_form_id = ir_model_data.xmlid_to_res_id(
                'mail.email_compose_message_wizard_form')
        except ValueError:
            compose_form_id = False
        ctx = {
            'default_model': 'sales.return',
            'default_res_id': self.ids[0],
            'default_use_template': bool(template_id),
            'default_template_id': template_id,
            'default_composition_mode': 'comment',
            'default_user_id': self.env.user.id,
        }
        action = {
            'name': _('Compose Email'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form_id, 'form')],
            'view_id': compose_form_id,
            'target': 'new',
            'context': ctx,
        }
        return action

    
    # def send_approve_service(self):
    #     for record in self:
    #         record.state = 'approved'
         

    # def return_advance(self):
    #     inv_obj = self.env['account.move'].search(
    #         [('invoice_origin', '=', self.name)])
    #     inv_ids = []
    #     for each in inv_obj:
    #         inv_ids.append(each.id)
    #     view_id = self.env.ref('account.view_move_form').id

    #     if inv_ids:
    #         if len(inv_ids) <= 1:
    #             value = {
    #                 'view_mode': 'form',
    #                 'res_model': 'account.move',
    #                 'view_id': view_id,
    #                 'type': 'ir.actions.act_window',
    #                 'name': 'Invoice',
    #                 'res_id': inv_ids[0]
    #             }
    #         else:
    #             value = {
    #                 'domain': str([('id', 'in', inv_ids)]),
    #                 'view_mode': 'tree,form',
    #                 'res_model': 'account.move',
    #                 'view_id': False,
    #                 'type': 'ir.actions.act_window',
    #                 'name': 'Invoice',
    #                 'res_id': inv_ids[0]
    #             }

    #         return value
    #     else:
    #         raise UserError("No invoice created")
        

    # def _invoice_count(self):
    #     """Calculating the number of invoices"""
    #     move_ids = self.env['account.move'].search([('invoice_origin', '=', self.name)])
    #     self.invoice_count = len(move_ids)
 
    
    # def _advance_payment_count(self):
    #     for rec in self:
    #         payment_ids = self.env['account.payment'].search([('partner_id', '=', rec.partner_id.id), ('state', '=', 'draft')])
    #         total_amount = sum(payment.amount for payment in payment_ids)
    #         rec.advance_payment_count = total_amount
               

    # def action_invoice_create_wizard(self):
    #     """opening a wizard to create invoice"""
    #     return {
    #         'name': _('Advance Payment'),
    #         'view_mode': 'form',
    #         'res_model': 'watch.invoice',
    #         'type': 'ir.actions.act_window',
    #         'target': 'new'
    #     }
        
    
    # def action_invoice_create(self):
    #     """Creating invoice"""
    #     self.write({'state': 'done'})

    #     # Create the 'Watch Service Charge' product if it doesn't exist
    #     product_id = self.env['product.product'].search([("name", "=", "Watch Service Charge")])
    #     if not product_id:
    #         vals1 = self._prepare_service_product()
    #         product_id = self.env['product.product'].create(vals1)

    #     self.first_invoice_created = True
    #     inv_obj = self.env['account.move']
    #     supplier = self.partner_id

    #     inv_data = {
    #         'move_type': 'out_invoice',
    #         'ref': supplier.name,
    #         'partner_id': supplier.id,
    #         'currency_id': self.company_id.currency_id.id,
    #         'journal_id': self.journal_type.id,
    #         'invoice_origin': self.name,
    #         'company_id': self.company_id.id,
    #     }

    #     inv_id = inv_obj.create(inv_data)
    #     self.first_payment_inv = inv_id.id
    #     self.number = self.name

    #     income_account = False  # Initialize income_account variable

    #     # Add the 'ProductService Charge' product as the first line
    #     if product_id:
    #         invoice_lines = [(0, 0, {
    #             'name': product_id.name,
    #             'price_unit': product_id.list_price,
    #             'quantity': 1,
    #             'credit': product_id.list_price,
    #             'debit': 0,
    #             'account_id': income_account,
    #             'product_id': product_id.id,
    #             'move_id': inv_id.id,
    #         })]
    #     else:
    #         invoice_lines = []

    #     # Search for product.order.line records
    #     sale_order_products = self.env['product.order.line'].search([('product_order_id', '=', self.name)])

    #     for line_data in sale_order_products:
    #         qty = line_data.product_uom_qty - line_data.qty_invoiced
    #         if qty > 0:
    #             price = line_data.product_id.list_price
    #             uom_id = line_data.product_id.product_tmpl_id.uom_id

    #             # Create invoice line data and append it to the list
    #             invoice_line_data = (0, 0, {
    #                 'name': line_data.product_id.name,
    #                 'price_unit': price,
    #                 'quantity': qty,
    #                 'product_uom_id': uom_id.id,
    #                 'credit': price,
    #                 'debit': 0,
    #                 'account_id': income_account,
    #                 'product_id': line_data.product_id.id,
    #                 'move_id': inv_id.id,
    #             })

    #             invoice_lines.append(invoice_line_data)

    #     # Write all invoice line data at once after the loop has finished
    #     inv_id.write({
    #         'invoice_line_ids': invoice_lines
    #     })

    #     # Recompute payment term lines
    #     inv_id._recompute_payment_terms_lines()


    #     # Handle the case where no invoice lines were created
    #     if not invoice_lines:
    #         raise UserError(_('Nothing to create invoice'))

    #     imd = self.env['ir.model.data']
    #     action = imd.xmlid_to_object('account.action_move_out_invoice_type')
    #     list_view_id = imd.xmlid_to_res_id('account.view_move_tree')
    #     form_view_id = imd.xmlid_to_res_id('account.view_move_form')
    #     result = {
    #         'name': action.name,
    #         'help': action.help,
    #         'type': 'ir.actions.act_window',
    #         'views': [[list_view_id, 'tree'], [form_view_id, 'form'], [False, 'graph'], [False, 'kanban'],
    #                 [False, 'calendar'], [False, 'pivot']],
    #         'target': action.target,
    #         'context': action.context,
    #         'res_model': 'account.move',
    #     }
    #     if len(inv_id) > 1:
    #         result['domain'] = "[('id','in',%s)]" % inv_id.ids
    #     elif len(inv_id) == 1:
    #         result['views'] = [(form_view_id, 'form')]
    #         result['res_id'] = inv_id.ids[0]
    #     else:
    #         result = {'type': 'ir.actions.act_window_close'}
        
    #     return result


    # def _stage_find(self, team_id=False, domain=None, order='sequence'):
    #     """ Determine the stage of the current lead with its teams, the given domain and the given team_id
    #         :param team_id
    #         :param domain : base search domain for stage
    #         :returns crm.stage recordset
    #     """
    #     # collect all team_ids by adding given one, and the ones related to the current leads
    #     # team_ids = set()
    #     # if team_id:
    #     #     team_ids.add(team_id)
    #     # for lead in self:
    #     #     if lead.team_id:
    #     #         team_ids.add(lead.team_id.id)
    #     # # generate the domain
    #     # if team_ids:
    #     #     search_domain = ['|', ('team_id', '=', False), ('team_id', 'in', list(team_ids))]
    #     # else:
    #     search_domain = []
    #     # AND with the domain in parameter
    #     if domain:
    #         search_domain += list(domain)
    #     # perform search, return the first found
    #     return self.env['sales.return.stage'].search(search_domain, order=order, limit=1)
    
    
    # def action_unarchive(self):
    #     """ Set (x_)active=True on a recordset, by calling toggle_active to
    #         take the corresponding actions according to the model
    #     """
    #     return self.filtered(lambda record: not record[self._active_name]).toggle_active()

    
    # def _register_hook(self):
    #     """ stuff to do right after the registry is built """
    #     pass

    
    # def _unregister_hook(self):
    #     """ Clean up what `~._register_hook` has done. """
    #     pass

    
    # def action_set_damage(self):
    #     """ Won semantic: probability = 100 (active untouched) """
    #     # self.action_unarchive()
    #     # group the leads by team_id, in order to write once by values couple (each write leads to frequency increment)
    #     damage_stage = {}
    #     for lead in self:
    #         stage_id = lead._stage_find(domain=[('is_damage', '=', True)])
    #         if stage_id in damage_stage:
    #             damage_stage[stage_id] |= lead
    #         else:
    #             damage_stage[stage_id] = lead
    #     for damage_stage_id, leads in damage_stage.items():
    #         leads.write({'stage_id': damage_stage_id.id})
    #     return True

    
    # def _prepare_service_product(self):
    #     return {
    #         'name': 'Product Service Charge',
    #         'type': 'service',
    #         'invoice_policy': 'order',
    #         'company_id': False,
    #     }      

    
    # def action_post_stock(self):
    #     flag = 0
    #     for order in self.product_order_line:
    #         if order.product_uom_qty > order.qty_stock_move:
    #             flag = 1
    #             pick = {
    #                 'picking_type_id': self.picking_transfer_id.id,
    #                 'partner_id': self.partner_id.id,
    #                 'origin': self.name,
    #                 'location_dest_id': self.partner_id.property_stock_customer.id,
    #                 'location_id': self.picking_transfer_id.default_location_src_id.id,
    #             }

    #             picking = self.env['stock.picking'].create(pick)
    #             self.stock_picking_id = picking.id
    #             self.picking_count = len(picking)
    #             moves = order.filtered(
    #                 lambda r: r.product_id.type in ['product',
    #                                                 'consu'])._create_stock_moves_transfer(
    #                 picking)
    #             move_ids = moves._action_confirm()
    #             move_ids._action_assign()
    #         if order.product_uom_qty < order.qty_stock_move:
    #             raise UserError(
    #                 _('Used quantity is less than quantity stock move posted. '))
    #     if flag != 1:
    #         raise UserError(_('Nothing to post stock move'))
    #     if flag != 1:
    #         raise UserError(_('Nothing to post stock move'))
        

    # def action_view_invoice(self):
    #     self.ensure_one()
    #     ctx = dict(
    #         create=False,
    #     )
    #     action = {
    #         'name': _("Invoices"),
    #         'type': 'ir.actions.act_window',
    #         'res_model': 'account.move',
    #         'target': 'current',
    #         'context': ctx
    #     }
    #     move_ids = self.env['account.move'].search(
    #         [('invoice_origin', '=', self.name)])
    #     inv_ids = []
    #     for each in move_ids:
    #         inv_ids.append(each.id)
    #     if len(move_ids) == 1:
    #         invoice = inv_ids and inv_ids[0]
    #         action['res_id'] = invoice
    #         action['view_mode'] = 'form'
    #         action['views'] = [
    #             (self.env.ref('account.view_move_form').id, 'form')]
    #     else:

    #         action['view_mode'] = 'tree,form'
    #         action['domain'] = [('id', 'in', inv_ids)]
    #     return action

   
    # def action_view_payment(self):
    #     payments = self.env['account.payment'].search([('partner_id', '=', self.partner_id.id), ('payment_type', '=', 'inbound'), ('state', '=', 'draft')])
    #     if payments:
    #         action = {
    #             'name': 'Advance Payment',                                  
    #             'type': 'ir.actions.act_window',
    #             'view_mode': 'tree,form',
    #             'res_model': 'account.payment',
    #             'views': [(False, 'tree'), (False, 'form')],
    #             'domain': [('id', 'in', payments.ids)],
    #             'context': {'create': False}
    #         }
    #     else:
    #         action = {'type': 'ir.actions.act_window_close'}
    #     return action  
   
    
    def get_ticket(self):
        self.ensure_one()
        user = self.env['res.users'].browse(self.env.uid)
        if user.tz:
            tz = pytz.timezone(user.tz)
            time = pytz.utc.localize(datetime.now()).astimezone(tz)
            date_today = time.strftime("%Y-%m-%d %H:%M %p")
        else:
            date_today = datetime.strftime(datetime.now(),
                                           "%Y-%m-%d %I:%M:%S %p")
        complaint_text = ""
        description_text = ""
        complaint_id = self.env['sales.return.complain.tree'].search(
            [('complaint_id', '=', self.id)])
        if complaint_id:
            for obj in complaint_id:
                complaint = obj.complain_type_tree
                description = obj.description_tree
                complaint_text = complaint.complain_type + ", " + complaint_text
                if description.description:
                    description_text = description.description + ", " + description_text
        else:
            for obj in complaint_id:
                complaint = obj.complain_type_tree
                complaint_text = complaint.complain_type + ", " + complaint_text
        data = {
            'ids': self.ids,
            'model': self._name,
            'date_today': date_today,
            'date_request': self.date_request,
            'date_return': self.return_date,
            'sev_id': self.name,
            'warranty': self.is_in_warranty,
            'customer_name': self.partner_id.name,
            'watch_no': self.watch_no,
            'technician_name': self.technician_name.name,
            'complain_types': complaint_text,
            'complaint_description': description_text,
            'product_id': self.product_id.name,
            'expiry_date': self.expiry_date,
            'delivery_location_id': self.delivery_location_id.name,
            'receive_location_id': self.receive_location_id.name,
            'receive_by': self.receive_by.name,
            'diagnosis_by': self.diagnosis_by.name,

        }
        return self.env.ref('dsl_sales_return.sales_return_ticket').report_action(self, data=data)

    
class WatchBrand(models.Model):
    _name = 'watch.brand'
    _rec_name = 'brand_name'

    brand_name = fields.Char(string="Product Brand", required=True)


class SalesReturnComplainTree(models.Model):
    _name = 'sales.return.complain.tree'
    _rec_name = 'complain_type_tree'

    complaint_id = fields.Many2one('sales.return')

    complain_type_tree = fields.Many2one('sales.return.complain', string="Category",
                                          required=True)
    description_tree = fields.Many2one('sales.return.complain.description',
                                       string="Description",
                                       domain="[('complain_type_template','=',complain_type_tree)]")


class WatchBrandModels(models.Model):
    _name = 'brand.model'
    
    name = fields.Char(string="Model Name", required=True)
    watch_brand_name = fields.Many2one('watch.brand', string="Product Brand")
    image_medium = fields.Binary(string='image', store=True, attachment=True)


class WatchServiceTermsAndConditions(models.Model):
    _name = 'terms.conditions'
    _rec_name = 'terms_id'

    terms_id = fields.Char(string="Terms and condition", compute="_find_id")
    terms_conditions = fields.Text(string="Terms and Conditions")

    def _find_id(self):
        self.terms_id = self.id or ''


class WatchServiceDeliveryLocation(models.Model):
    _name = 'delivery.location'

    name = fields.Char(string="Delivery Location")
    

class WatchServiceProductType(models.Model):
    _name = 'product.type'

    name = fields.Char(string="Product Type")
    
    
class WatchServicecomplain(models.Model):
    _name = 'sales.return.complain'

    complain_type_id = fields.Many2one('sales.return.complain.type', string="complain")   
    description = fields.Text(string="Complaint Description") 
    sales_return_id = fields.Many2one('sales.return')
    

class WatchComplainType(models.Model):
    _name = 'sales.return.complain.type'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'complain_type'

    complain_type = fields.Char(string="Complaint Type", required=True)
    description = fields.Text(string="Complaint Description")
    sales_return_id = fields.Many2one('sales.return')


class WatchComplaintTypeTemplate(models.Model):
    _name = 'sales.return.complain.description'
    _rec_name = 'description'

    complain_type_template = fields.Many2one('sales.return.complain', string="Complaint Type Template", required=True)
    description = fields.Text(string="Complaint Description")
    complaint_id = fields.Many2one('sales.return')
    

class ResPartnerPhone(models.Model):
    _inherit = "res.partner"

    @api.model
    def _name_search(self, name='', args=None, operator='ilike', limit=100,
                     name_get_uid=None):
        if args is None:
            args = []
        domain = args + ['|', ('name', operator, name), ('phone', operator, name)]
        return self._search(domain+args, limit=limit, access_rights_uid=name_get_uid)   