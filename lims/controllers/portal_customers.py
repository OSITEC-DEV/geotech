# -*- coding: utf-8 -*-
from odoo import fields, http, _
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager, get_records_pager
from odoo.exceptions import AccessError, MissingError
from odoo.http import request
import binascii


class CustomerPortalRequest(CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        partner = request.env.user.partner_id

        MedicalRequest = request.env['lims.sample.main']
        if 'request_count' in counters:
            values['request_count'] = MedicalRequest.sudo().search_count(self._prepare_requests_domain(partner)) \
                if MedicalRequest.sudo().check_access_rights('read', raise_exception=False) else 0
        return values

    def _report_get_page_view_values(self, req, access_token, **kwargs):
        values = {
            'req': req,
            'token': access_token,
            'return_url': '/my',
            'bootstrap_formatting': True,
            'partner_id': req.partner_id.id,
            'report_type': 'html',
            'page_name': 'medical_request_form',
            'action': req._get_portal_return_action(),
        }
        if req.company_id:
            values['res_company'] = req.company_id
        history = False
        if req.state not in ('reject'):
            history = request.session.get('my_request_history', [])
        values = self._get_page_view_values(
            req, access_token, values, 'my_subscriptions_history', False)

        return values

    @http.route(['/my/requests/<int:req_id>'], type='http', auth="user", website=True)
    def portal_report_page(self, req_id, report_type=None, access_token=None, message=False, download=False, **kw):
        try:
            report_sudo = self._document_check_access('lims.sample.main', req_id, access_token=access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        if report_type in ('pdf', 'text'):
            return self._show_report(model=report_sudo, report_type=report_type,
                                     report_ref='lims.medical_lab_analysis_report', download=download)
        if report_sudo:
            # store the date as a string in the session to allow serialization
            now = fields.Date.today().isoformat()
            session_obj_date = request.session.get('view_report_%s' % report_sudo.id)
            if session_obj_date != now and request.env.user.share and access_token:
                request.session['view_report_%s' % report_sudo.id] = now
                body = _('Request viewed by customer %s', report_sudo.partner_id.name)
                report_sudo.message_post(
                    body=body,
                    message_type="notification",
                    subtype_xmlid="mail.mt_note",
                    partner_ids=report_sudo.user_id.sudo().partner_id.ids,
                )
        values = self._report_get_page_view_values(report_sudo, access_token, **kw)
        values['message'] = message
        return request.render('lims.medical_analysis_report_portal_content', values)

    def _prepare_requests_domain(self, partner):
        return [
            ('message_partner_ids', 'in', partner.ids),
            ('state', 'not in', ['reject'])
        ]

    @http.route(['/my/requests', '/my/requests/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_requests(self, page=1, date_begin=None, date_end=None, search="", groupby='none', search_in="All",
                           sortby=None, **kw):
        values = self._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        MedicalRequest = request.env['lims.sample.main']

        domain = self._prepare_requests_domain(partner)
        if not groupby:
            groupby = "none"
        searchbar_sortings = {
            'date': {'label': _('Request Date'), 'order': 'date desc'},
            'name': {'label': _('Request N'), 'order': 'name'},
            'Customer': {'label': _('Customer'), 'order': 'partner_id'}
            # 'stage': {'label': _('Stage'), 'order': 'state'},
        }
        searchbar_inputs = {
            "All": {"label": "All", "input": "All", "domain": domain},
            "Customer": {"label": "Customer", "input": "Customer", "domain": domain + [("partner_id", "ilike", search)]},
            "Request": {"label": "Request N", "input": "Request", "domain": domain + [("name", "ilike", search)]},
            "Accession_number": {"label": "Accession N", "input": "Accession_number",
                                 "domain": domain + [("external_accession_number", "ilike", search)]},
        }

        # default sortby order
        if not sortby:
            sortby = 'date'
        sort_order = searchbar_sortings[sortby]['order']
        search_domain = searchbar_inputs[search_in]["domain"]
        # count for pager
        request_count = MedicalRequest.sudo().search_count(domain)
        # pager
        pager = portal_pager(
            url="/my/requests",
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby},
            total=request_count,
            page=page,
            step=self._items_per_page
        )
        # content according to pager
        request_ids = MedicalRequest.sudo().search(search_domain, order=sort_order, limit=self._items_per_page,
                                                   offset=pager['offset'])
        request.session['my_request_history'] = request_ids.ids[:100]

        values.update({
            'date': date_begin,
            'request_ids': request_ids,
            'page_name': 'Requests',
            'pager': pager,
            'default_url': '/my/requests',
            'search_in': search_in,
            'groupby': groupby,
            'searchbar_sortings': searchbar_sortings,
            'searchbar_inputs': searchbar_inputs,
            'sortby': sortby,
        })
        return request.render("lims.portal_my_requests", values)

    @http.route(['/my/requests/<int:req_id>/accept'], type='json', auth="user", website=True)
    def portal_route_accept(self, req_id, access_token=None, name=None, signature_image=None, **post):

        access_token = access_token or request.httprequest.args.get('access_token')

        try:
            request_sudo = self._document_check_access('lims.sample.main', req_id, access_token=access_token)

        except (AccessError, MissingError):
            return {'error': _('Invalid request.')}

        if not signature_image:
            return {'error': _('Signature_image is missing.')}

        try:
            request_sudo.write({
                'signature_consult': signature_image,
            })
            for report in request_sudo.report_ids:
                try:
                    report.sudo().write({'state': 'sent',
                                         'consultant_id': request.session.uid,
                                         'consultation_date': fields.datetime.now()})
                except (AccessError, MissingError):
                    return {'error': _('No report found')}
        except (TypeError, binascii.Error) as e:
            return {'error': _('Invalid signature_image data.')}

        # query_string = '&message=sign_ok'

        # _url = route_sudo.get_portal_url(query_string=query_string)

        # _logger.info("url -----------------------------------------------------------------")
        # _logger.info(_url)

        return {
            'force_refresh': True,
            'redirect_url': request_sudo.get_portal_url(),
        }
