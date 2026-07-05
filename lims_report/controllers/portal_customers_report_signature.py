# -*- coding: utf-8 -*-
from odoo import fields, http, _
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager, get_records_pager
from odoo.exceptions import AccessError, MissingError
from odoo.http import request
from odoo.tools import groupby as groupbyelem
from operator import itemgetter
import binascii


class CustomerPortalTestSignature(CustomerPortal):


    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if 'report_2sign_count' in counters:
            MedicalReport = request.env['lims.report']
            domain = self._prepare_reports_tosign_domain()
            values['report_2sign_count'] = MedicalReport.sudo().search_count(domain)
        return values


    def _prepare_reports_tosign_domain(self, partner):
        return [
            ('message_partner_ids', 'in', partner.ids),
            ('state', 'in', ['valid']),
            ('consultant_id', '=', False),
        ]

    @http.route(['/my/reports/to_sign', '/my/reports/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_reports_to_sign(self, page=1, date_begin=None, date_end=None, search="", groupby='none',
                                  search_in="All", sortby=None, **kw):
        values = self._prepare_portal_layout_values()

        partner = request.env.user.partner_id
        MedicalReport = request.env['lims.report'].sudo()
        domain = [('id', '=', -1)]
        if request.env.user.has_group('lims.group_lims_portal_consultant'):
            domain = self._prepare_reports_tosign_domain(partner)
        if not groupby:
            groupby = "none"
        searchbar_sortings = {
            'date': {'label': _('Report Date'), 'order': 'date desc'},
            'name': {'label': _('Reference'), 'order': 'name'},
            'Customer': {'label': _('Customer'), 'order': 'partner_id'}
            # 'stage': {'label': _('Stage'), 'order': 'state'},
        }
        searchbar_inputs = {
            "All": {"label": "All", "input": "All", "domain": domain},
            "Customer": {"label": "Customer", "input": "Customer", "domain": domain + [("partner_id", "ilike", search)]},
            "Report": {"label": "Report N", "input": "Report", "domain": domain + [("name", "ilike", search)]},
            "Accession_number": {"label": "Accession N", "input": "Accession_number",
                                 "domain": domain + [("main_id.external_accession_number", "ilike", search)]},
        }

        groupby_list = {
            'none': {'input': 'none', 'label': _("None"), "order": 1},
            'print_group_id': {'input': 'print_group_id', 'label': _("Category"), "order": 1},
            'partner_id': {'input': 'partner_id', 'label': _("Customer"), "order": 1},
        }
        report_group_by = groupby_list.get(groupby, {})

        # default sortby order
        if not sortby:
            sortby = 'date'
        sort_order = searchbar_sortings[sortby]['order']
        search_domain = searchbar_inputs[search_in]["domain"]
        if groupby in ("print_group_id", "partner_id"):
            report_group_by = report_group_by.get("input")
            sort_order = report_group_by + "," + sort_order
        else:
            report_group_by = ''
            pass
        # count for pager
        report_count = MedicalReport.search_count(domain)
        # pager
        pager = portal_pager(
            url="/my/reports/to_sign",
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby, 'groupby': groupby},
            total=report_count,
            page=page,
            step=self._items_per_page
        )
        # content according to pager
        reports = MedicalReport.search(search_domain, order=sort_order, limit=self._items_per_page,
                                       offset=pager['offset'])
        if report_group_by:
            report_group_list = [{report_group_by: k, 'reports': MedicalReport.concat(*g)} for k, g in
                                 groupbyelem(reports.sudo(), itemgetter(report_group_by))]
        else:
            report_group_list = [{'reports': reports.sudo()}]

        request.session['my_reports_toSign_history'] = reports.ids[:100]

        values.update({
            'date': date_begin,
            'group_reports': report_group_list,
            # 'reports': reports.sudo(),
            'page_name': 'medical_report_list',
            'pager': pager,
            'default_url': '/my/reports/to_sign',
            'search_in': search_in,
            'groupby': groupby,
            'searchbar_groupby': groupby_list,
            'searchbar_sortings': searchbar_sortings,
            'searchbar_inputs': searchbar_inputs,
            'sortby': sortby,
        })
        return request.render("lims_report.portal_my_reports_by_pending", values)

    @http.route(['/my/reports/<model("lims.report"):report_id>/accept'], type='json', auth="user", website=True)
    def portal_route_accept(self, report_id, access_token=None, name=None, signature_image=None, **post):

        access_token = access_token or request.httprequest.args.get('access_token')
        try:
            report_sudo = self._document_check_access('lims.report', report_id.id, access_token=access_token)

        except (AccessError, MissingError):
            return {'error': _('Invalid request.')}

        if not signature_image:
            return {'error': _('Signature is missing.')}

        try:
            report_sudo.sudo().write({'consultant_id': request.env.user,
                                      'consultation_date': fields.Datetime.now(),
                                      'signature_consult': request.env.user.signature_image or signature_image})
        except (TypeError, binascii.Error) as e:
            return {'error': _('Invalid signature_image data.')}

        # query_string = '&message=sign_ok'

        # _url = route_sudo.get_portal_url(query_string=query_string)

        # _logger.info("url -----------------------------------------------------------------")
        # _logger.info(_url)

        return {
            'force_refresh': True,
            'redirect_url': report_sudo.get_portal_url(report_type='html'),
        }
