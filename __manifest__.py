# -*- coding: utf-8 -*-
{
    'name': 'Sales Return',
    'summary': """Manage Sales Return.""",
    'description': " ",
    'version': '14.0.1.0',
    'author': 'DSL',
    'website': '',
    'category': '',
    'depends': [
        'base',
        'web',
        'sale',
        'account',
        'product',
        'stock',
        'product_warranty',
        'dsl_inventory_customization',
        'dsl_sale_management',
        'dsl_external_entries',
        'dsl_scrap_management',
        'dsl_smart_inventory_adjustment',
        'multi_level_approval',
    ],
    'data': [
        ## Report
        'reports/sales_return_ticket.xml',
        'reports/sales_return_ticket_template.xml',
        
        ## Data
        'data/ir_sequence.xml',
        'data/sales_return_stage_demo_data.xml',
        'data/sales_return_tracker_mail_template.xml',

        ## Security
        'security/ir.model.access.csv',
        
        ## Wizard
        'wizards/stock_scrap_management_wizard_views.xml',
        'wizards/sales_return_expense_entries_views.xml',
        # 'wizards/dsl_expense_entries_wizard_views.xml',
        
        ## View
        'views/res_config_settings_views.xml',
        'views/sales_return_views.xml',
        'views/sales_return_complain_type_views.xml',
        'views/sales_return_stage_views.xml',
        'views/sale_order_line_views.xml',
        'views/menus.xml',
    ],
   'icon':  'dsl_sales_return/static/description/icon.png',
    'installable': True,
    'auto_install': False,
    'application': True,
    'price': 0,
}
