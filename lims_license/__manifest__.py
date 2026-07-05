# -*- coding: utf-8 -*-
{
    'name': 'LIMS License Protection',
    'summary': """
           Offline signed-license validation for on-premise LIMS deployments.
                """,
    'description': """
        Ships only a public key. Validates a signed .lic license file issued
        by the vendor's separate, private license-generator tool. Works
        without any internet/activation-server dependency, so it does not
        interfere with air-gapped or fully offline on-premise installs.

        Enforcement is soft-then-hard: a persistent banner and logged
        warnings during a configurable grace period after a license becomes
        invalid or expires, followed by a hard block of non-administrator
        users once the grace period elapses.
    """,
    'version': '18.0.1.0',
    'sequence': 1,
    'website': "",
    'category': 'Extra Tools',
    'author': 'Oussama Sekkak',
    'maintainer': 'Oussama Sekkak',

    'depends': [
        'lims',
        'web',
    ],
    'external_dependencies': {
        'python': ['cryptography'],
    },
    'data': [
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'data/ir_cron_data.xml',
        'views/lims_license_views.xml',
        'views/menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'lims_license/static/src/js/license_banner.js',
            'lims_license/static/src/css/license_banner.css',
        ],
    },
    'demo': [],
    'auto_install': False,
    'application': False,
    'installable': True,
    'license': 'OPL-1',
}
