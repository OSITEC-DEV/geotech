# -*- coding: utf-8 -*-
{
    'name': 'Lims system',
    'summary': """
            From the sample registration to report creation and submitting.
                """,
    'description': """Laboratory management """,
    'version': '18.0.1.1',
    'sequence': 15,
    'website': "",
    'category': 'Extra Tools',
    'author': 'OSITEC LLC',
    'maintainer': 'OSITEC LLC',
    'depends': [
        'account',
        'sale',
        'purchase',
        'product',
        'hr',
        'web_map'
    ],
    'data': [
        'security/lims_security.xml',
        'security/ir.model.access.csv',
        'views/product_views.xml',
        'views/res_partner_view.xml',
        'views/res_users_view.xml',
        'views/lims_views.xml',
        'views/lims_analysis.xml',
        'views/lims_department_view.xml',
        'views/lims_sample_preparation.xml',
        'views/lims_methods_view.xml',
        'views/menus.xml',
        'views/company.xml',
        'views/res_config_settings_view.xml',
        'views/portal_report.xml',
        'views/final_report.xml',
        'views/label_report.xml',
        'views/sale_report_templates.xml',
        'views/lims_laboratory_views.xml',
        'views/unlock_wizard_view.xml',
        'views/create_pack_wizard_view.xml',
        'data/lims_data.xml',
        'views/lock_cron.xml',
    ],
    'demo': [],
    'assets': {
        'point_of_sale.assets': [
            'pos_fp_by_partner/static/src/js/js.js',
        ],
        'web.assets_backend': [
            'lims/static/src/css/vertical_text.css',
        ]
    },
    'qweb': [],
    'images': ['static/description/banner.gif'],
    'auto_install': False,
    'application': True,
    'installable': True,
    'license': 'OPL-1',
}
