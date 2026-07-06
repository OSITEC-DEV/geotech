# -*- coding: utf-8 -*-
{
    'name': 'Report for LIMS',
    'summary': """
            This module allows you print report related to LIMS Modules.
                """,
    'description': """Report LIMS""",
    'version': '19.0.1.0',
    'sequence': 15,
    'website': "",
    'category': 'Extra Tools',
    'author': 'Oussama Sekkak',
    'maintainer': 'Oussama Sekkak',
    'depends': [
        'lims',
        'portal'
    ],
    'data': ['security/ir.model.access.csv',
             'security/lims_security.xml',
             'views/lims_view.xml',
             'views/report_view.xml',
             'views/lims_department_view.xml',
             'views/analysis_report.xml',
             'views/portal_report.xml',
             'views/product_views.xml',
             'data/lims_sequence_data.xml', ],
    'demo': [],
    'images': ['static/description/banner.gif'],
    'auto_install': False,
    'application': True,
    'installable': True,
    'license': 'OPL-1',
}
