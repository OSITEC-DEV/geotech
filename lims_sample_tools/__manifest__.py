# -*- coding: utf-8 -*-
{
    'name': 'LIMS Sample Tools',
    'summary': """
           Request dashboard, bulk sample editing, camera capture, and test catalogue picker.
                """,
    'description': """
        Generalized versions of five sample-registration UX features originally
        built for the food LIMS vertical, adapted to work on core lims fields
        only (no SFDA/pesticide/shelf-life/multi-unit food concepts):
        - Request dashboard kanban (by request category)
        - Request configuration lines (product/quantity/frequency/department,
          no automatic accounting distribution)
        - Bulk sample-edit wizard (note, collector, sample date)
        - Sample photo capture page (/lims/camera)
        - Test/parameter catalogue picker widget (filtered by sample type)
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
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/lims_sample_main_views.xml',
        'views/lims_request_dashboard_kanban_views.xml',
        'views/lims_request_config_line_views.xml',
        'views/lims_sample_wizard_views.xml',
        'views/product_template_views.xml',
        'views/menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'lims_sample_tools/static/src/js/catalogue_widget.js',
            'lims_sample_tools/static/src/xml/catalogue_widget.xml',
            'lims_sample_tools/static/src/css/catalogue_widget.css',
            'lims_sample_tools/static/src/css/request_kanban.css',
        ],
    },
    'demo': [],
    'auto_install': False,
    'application': False,
    'installable': True,
    'license': 'OPL-1',
}
