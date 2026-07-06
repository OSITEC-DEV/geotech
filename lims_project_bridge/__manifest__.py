# -*- coding: utf-8 -*-
{
    'name': 'LIMS Project Bridge',
    'summary': """
           Links geotechnical sites, special-project permits, and rig
           deployments to Odoo Project tasks.
                """,
    'description': """
        Bridges the LIMS layer to Odoo's Project app, matching the RFP's
        stated flow: a project is generated from the confirmed sales order
        (via core Odoo's own sale/project bridge), then a standard set of
        tasks (Site Preparation, Mobilization, Test Execution, Data Entry &
        Report Drafting) is generated for the site or permit on demand.

        Rig deployments and boreholes link to a specific task so the
        Project Gantt/Kanban reflects real field work, without duplicating
        the technical data that stays in the LIMS models themselves.

        Task generation and date syncing are written defensively against
        project.task's exact field names, since this targets a very recent
        Odoo version whose Project app internals could not be verified
        against a live instance while building this.
    """,
    'version': '19.0.1.0',
    'sequence': 16,
    'website': "",
    'category': 'Extra Tools',
    'author': 'Oussama Sekkak',
    'maintainer': 'Oussama Sekkak',

    'depends': [
        'lims_geotech',
        'lims_rig',
        'lims_special_project',
        'lims_sample_tools',
        'sale_project',
    ],
    'data': [
        'views/lims_geotech_site_views.xml',
        'views/lims_geotech_borehole_views.xml',
        'views/lims_rig_schedule_views.xml',
        'views/lims_special_project_permit_views.xml',
        'views/lims_request_config_line_views.xml',
    ],
    'demo': [],
    'auto_install': False,
    'application': False,
    'installable': True,
    'license': 'OPL-1',
}
