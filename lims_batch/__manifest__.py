# -*- coding: utf-8 -*-
{
    'name': 'LIMS Batches',
    'summary': """
           This module allows you to manage analysis by batches .
                """,
    'description': """Management of a medical laboratory """,
    'version': '18.0.1.0',
    'sequence': 15,
    'website': "",
    'category': 'Extra Tools',
    'author': 'Oussama Sekkak',
    'maintainter': 'Oussama Sekkak',

    'depends': [
        'lims',
        'lims_method',
        'lims_result',
        'stock',
        'hr'
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/lims_analysis.xml',
        'views/lims_batch_view.xml',
        'views/lims_batch_kit_view.xml',
        'views/lims_batch_wizard.xml',
        'views/hr_employee_view.xml',
        'views/menus.xml',
        'data/data.xml'

    ],
    'demo': [],
    'images': ['static/description/banner.gif'],
    'auto_install': False,
    'application': True,
    'installable': True,
    'license': 'OPL-1',
}
