# -*- coding: utf-8 -*-
{
    'name': 'LIMS RIG Management',
    'summary': """
           Fleet, scheduling, and deployment management for soil testing rigs.
                """,
    'description': """Rig Management for Geotechnical Laboratory""",
    'version': '19.0.1.0',
    'sequence': 15,
    'website': "",
    'category': 'Extra Tools',
    'author': 'Oussama Sekkak',
    'maintainer': 'Oussama Sekkak',

    'depends': [
        'lims',
        'lims_license',
        'project',
        'sale',
        'maintenance',
        'fleet',
    ],
    'data': [
        'security/lims_rig_security.xml',
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'views/lims_rig_views.xml',
        'views/lims_rig_schedule_views.xml',
        'views/menus.xml',
    ],
    'demo': [],
    'images': ['static/description/icon.png'],
    'auto_install': False,
    'application': True,
    'installable': True,
    'license': 'OPL-1',
}
