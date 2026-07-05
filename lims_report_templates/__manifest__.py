# -*- coding: utf-8 -*-
{
    'name': 'Analysis Report Templates for LIMS',
    'summary': """
            This module allows you print analysis report related to tests parameters.
                """,
    'description': """Analysis Report Templates LIMS""",
    'version': '18.0.1.0',
    'sequence': 15,
    'website': "",
    'category': 'Extra Tools',
    'author': 'MOHAMMED RIDA YAHLA',
    'maintainter': 'MOHAMMED RIDA YAHLA',
    'depends': [
        'lims',
        'lims_method',
        'lims_report',
    ],

    'data': ['views/lims_analysis.xml',
             'views/lims_analysis_report.xml',
             'views/product_template.xml',
             'views/menus.xml',
             'views/report_view.xml',
             'report/analysis_report.xml',
             'report/lims_report_pdf_progress_bar.xml',
             'security/ir.model.access.csv',
             'report/Ajal_new_report.xml',
             ],
    'assets': {
    'web.report_assets_common': [
            'lims_report_templates/static/src/css/analysis_report.css',
        ],
    },
    'demo': [],
    'auto_install': False,
    'application': True,
    'installable': True,
    'license': 'OPL-1',
}