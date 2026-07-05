# -*- coding: utf-8 -*-
{
    'name': 'LIMS Geotechnical',
    'summary': """
           Site, borehole and geotechnical test management (SPT, Permeability, Packer, etc.) for LIMS.
                """,
    'description': """Geotechnical Laboratory Module""",
    'version': '19.0.1.0',
    'sequence': 15,
    'website': "",
    'category': 'Extra Tools',
    'author': 'Oussama Sekkak',
    'maintainer': 'Oussama Sekkak',

    'depends': [
        'lims',
        'lims_license',
        'lims_rig',
        'project',
        'sale',
    ],
    'data': [
        'security/lims_geotech_security.xml',
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'views/lims_geotech_site_views.xml',
        'views/lims_geotech_borehole_views.xml',
        'views/lims_geotech_test_spt_views.xml',
        'views/menus.xml',
    ],
    'demo': [],
    'auto_install': False,
    'application': True,
    'installable': True,
    'license': 'OPL-1',
}
