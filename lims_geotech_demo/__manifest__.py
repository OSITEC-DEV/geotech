# -*- coding: utf-8 -*-
{
    'name': 'LIMS Geotechnical Demo Data',
    'summary': """
           Sample data to test the geotechnical LIMS: sites, boreholes, SPT tests,
           rigs, schedules, and special project permits.
                """,
    'description': """
        Install this module on a test/staging database only to explore the
        geotechnical LIMS with realistic sample data. Uninstall it afterward
        to cleanly remove every demo record - none of this is meant to reach
        a real production database.
    """,
    'version': '19.0.1.0',
    'sequence': 20,
    'website': "",
    'category': 'Extra Tools',
    'author': 'Oussama Sekkak',
    'maintainer': 'Oussama Sekkak',

    'depends': [
        'lims_geotech',
        'lims_rig',
        'lims_special_project',
    ],
    'data': [
        'data/lims_laboratory_demo.xml',
        'data/res_partner_demo.xml',
        'data/hr_employee_demo.xml',
        'data/lims_rig_demo.xml',
        'data/lims_geotech_site_demo.xml',
        'data/lims_geotech_borehole_demo.xml',
        'data/lims_geotech_test_spt_demo.xml',
        'data/lims_special_project_demo.xml',
    ],
    'demo': [],
    'auto_install': False,
    'application': False,
    'installable': True,
    'license': 'OPL-1',
}
