# -*- coding: utf-8 -*-
from odoo import http
from odoo.addons.lims_report.controllers.portal_customers import CustomerPortalTest
from odoo.exceptions import AccessError, MissingError
from odoo.http import request


class CustomerPortalTestInherited(CustomerPortalTest):

    @http.route(['/my/reports/<model("lims.report"):report_id>'], type='http', auth="user", website=True)
    def portal_report_form_page(self, report_id, report_type=None, message=False, report_name=None, download=False,
                                access_token=None, **kw):
        access_token = access_token or request.httprequest.args.get('access_token')
        try:
            report_sudo = self._document_check_access('lims.report', report_id.id, access_token=access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        if report_type in ('pdf', 'text'):
            return self._show_report(model=report_sudo, report_type=report_type,
                                     report_ref=report_sudo.template_id.xml_id, download=download)
        else:
            vals = {'report': report_sudo, 'page_name': 'medical_report_form','message':message}
            history_session_key = 'my_reports_test_history'
            vals = self._get_page_view_values(
                report_sudo, access_token, vals, history_session_key, False)
            return request.render('lims_report.medical_analysis_report_form_view_portal', vals)

        super_ = super().portal_report_test_page(main_id=report_id, report_type=report_type, access_token=access_token,
                                                 message=message, download=download, **kw)
        return super_
