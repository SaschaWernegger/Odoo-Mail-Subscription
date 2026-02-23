# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'My Mail',
    'version': '0.1',
    'category': 'Tools',
    'sequence': 15,
    'summary': 'Manage mail and communication with opt-in and opt-out features',
    'website': 'https://www.odoo.com/app/mail',
    'depends': [
        'base_setup',
        'mail',
        'calendar',
        'contacts',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/mail_template_subscription_views.xml',
        'views/res_users_subscription_views.xml',
    ],
    'demo': [
        
    ],
    'installable': True,
    'application': True,
    'assets': {
        'web.assets_backend': [
            'my_mail/static/src/js/subscription_list_reload.js',
            'my_mail/static/src/js/user_subscription_grouped_list_view.js',
            'my_mail/static/src/scss/res_users_subscriptions.scss',
        ],
    },
    'author': 'Sascha Wernegger',
    'license': 'LGPL-3',
    'post_init_hook': 'post_init_hook',
}