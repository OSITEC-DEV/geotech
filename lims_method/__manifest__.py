# -*- coding: utf-8 -*-
{
    'name': 'Method Steps LIMS',
    'summary': """
           This module allows you to manage each analysis by steps before filling in the final result. .
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
        'maintenance',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/lims_method_step_views.xml',
        'views/lims_method_views.xml',
        'views/lims_analysis_views.xml',
        'views/maintenance_equipment_view.xml',
        'views/menus.xml',
        'views/product_views.xml',
    ],
    'demo': [],
    'images': ['static/description/banner.gif'],
    'auto_install': False,
    'application': True,
    'installable': True,
    'license': 'OPL-1',
}
