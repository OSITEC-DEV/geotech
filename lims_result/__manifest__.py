# -*- coding: utf-8 -*-
{
    'name': 'LIMS result',
    'summary': """
           This module allows you to manage the result by test by partner , delta check. .
                """,
    'description': """Management of a medical laboratory """,
    'version': '18.0.1.0',
    'sequence': 15,
    'website': "",
    'category': 'Extra Tools',
    'author': 'Oussama Sekkak',
    'maintainter': 'Oussama Sekkak',

    'depends': [
        'lims'
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/res_partner_view.xml',
        'views/lims_analysis.xml',
        'views/lims_batch_analysis.xml',
        'views/menus.xml',
        'views/lims_method_inherit.xml',
        'views/analysis_report.xml',
        'views/product_template.xml',

    ],
    'demo': [],
    'images': ['static/description/banner.gif'],
    'auto_install': False,
    'application': True,
    'installable': True,
    'license': 'OPL-1',
}
