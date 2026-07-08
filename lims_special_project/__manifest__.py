# -*- coding: utf-8 -*-
{
    'name': 'LIMS Special Projects (QC)',
    'summary': """
           Quality Control permits, site stations, and layer-based testing for Special Projects.
                """,
    'description': """
        Skeleton module for the Laboratory Special Projects / Quality Control scope
        (permits, site stations, layers). Field set intentionally minimal - to be
        finalized during requirement gathering workshops.
    """,
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
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'views/lims_special_project_permit_views.xml',
        'views/lims_special_project_station_views.xml',
        'views/menus.xml',
    ],
    'demo': [],
    'images': ['static/description/icon.png'],
    'auto_install': False,
    'application': True,
    'installable': True,
    'license': 'OPL-1',
}
