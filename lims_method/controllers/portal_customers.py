# -*- coding: utf-8 -*-
from odoo import fields, http, _
from odoo.addons.portal.controllers.portal import CustomerPortal, get_records_pager
from odoo.exceptions import AccessError, MissingError
from odoo.http import request


class CustomerPortal(CustomerPortal):

    # @http.route(['/my/report', '/my/report/page/<int:page>'], type='http', auth="user", website=True)
    # def portal_my_report(self, page=1, date_begin=None, date_end=None, sortby=None, **kw):
    # 	values = self._prepare_portal_layout_values()
    # 	partner = request.env.user.partner_id
    # 	Lims_sample = request.env['lims.sample.main']

    # 	searchbar_sortings = {
    # 		'date': {'label': _('Date report'), 'order': 'date desc'},
    # 		'name': {'label': _('Reference'), 'order': 'name'},
    # 	}

    # 	if date_begin and date_end:
    # 		domain += [('create_date', '>', date_begin), ('create_date', '<=', date_end)]

    # 	mainsample_count = Lims_sample.search_count(domain)

    # 	pager = portal_pager(
    # 		url="/my/report",
    # 		url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby},
    # 		total=mainsample_count,
    # 		page=page,
    # 		step=self._items_per_page
    # 	)

    # 	reports = Lims_sample.search(domain, order=sort_order, limit=self._items_per_page, offset=pager['offset'])

    # 	values.update({
    # 		'date': date_begin,
    # 		'reports': reports.sudo(),
    # 		'page_name': 'report',
    # 		'pager': pager,
    # 		'default_url': '/my/report',
    # 		'searchbar_sortings': searchbar_sortings,
    # 		'sortby': sortby,
    # 	})
    # 	return request.render("lims.medical_analysis_report_portal_content", values)

    def _report_get_page_view_values(self, report, access_token, **kwargs):
        values = {
            'report': report,
            'token': access_token,
            'return_url': '/my',
            'bootstrap_formatting': True,
            'partner_id': report.partner_id.id,
            'report_type': 'html',
            'action': report._get_portal_return_action(),
        }
        if report.company_id:
            values['res_company'] = report.company_id

        # if report.has_to_be_paid():
        #     domain = expression.AND([
        #         ['&', ('state', 'in', ['enabled', 'test']), ('company_id', '=', order.company_id.id)],
        #         ['|', ('country_ids', '=', False), ('country_ids', 'in', [order.partner_id.country_id.id])]
        #     ])
        #     acquirers = request.env['payment.acquirer'].sudo().search(domain)

        #     values['acquirers'] = acquirers.filtered(lambda acq: (acq.payment_flow == 'form' and acq.view_template_id) or
        #                                              (acq.payment_flow == 's2s' and acq.registration_view_template_id))
        #     values['pms'] = request.env['payment.token'].search([('partner_id', '=', order.partner_id.id)])
        #     values['acq_extra_fees'] = acquirers.get_acquirer_extra_fees(order.amount_total, order.currency_id, order.partner_id.country_id.id)
        history = []
        if report.state in ('tosend', 'done'):
            history = request.session.get('my_report_history', [])
        values.update(get_records_pager(history, report))

        return values

    @http.route(['/my/report/<int:main_id>'], type='http', auth="public", website=True)
    def portal_report_page(self, main_id, report_type=None, access_token=None, message=False, download=False, **kw):
        try:
            report_sudo = self._document_check_access('lims.sample.main', main_id, access_token=access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        if report_type in ('html', 'pdf', 'text'):
            return self._show_report(model=report_sudo, report_type=report_type,
                                     report_ref='lims.medical_lab_analysis_report', download=download)

        # use sudo to allow accessing/viewing orders for public user
        # only if he knows the private token
        # Log only once a day
        if report_sudo:
            # store the date as a string in the session to allow serialization
            now = fields.Date.today().isoformat()
            session_obj_date = request.session.get('view_report_%s' % report_sudo.id)
            if session_obj_date != now and request.env.user.share and access_token:
                request.session['view_report_%s' % report_sudo.id] = now
                body = _('Report viewed by customer %s', report_sudo.partner_id.name)
                report_sudo.message_post(
                    body=body,
                    message_type="notification",
                    subtype_xmlid="mail.mt_note",
                    partner_ids=report_sudo.user_id.sudo().partner_id.ids,
                )

        values = self._report_get_page_view_values(report_sudo, access_token, **kw)
        values['message'] = message

        return request.render('lims.medical_analysis_report_portal_content', values)

# @http.route(['/covid-19/result/<int:report_id>/<string:public_code>'], type='http', auth='public', website=True,)
# def get_medical_lab_result(self, public_code, report_id):
#     if public_code and report_id:
#         medical_report = request.env['test.result'].sudo().browse(report_id)
#         if medical_report:
#             return request.render('medical_lab.medical_test_result_portal_content', {'medical_report': medical_report})
#         else:
#             return request.render('http_routing.404')
#     else:
#         return request.render('http_routing.404')

# @http.route(['/my/report/<int:report_id>'], type='http', auth='public', website=True, )
# def get_document_reprot(self, report_id, report_type=None, access_token=None, message=False, download=False, **kw):
#     if report_id:
#         medical_report = request.env['test.result'].sudo().browse(report_id)
#         report = request.env.ref('medical_lab.medical_lab_analysis_report').sudo()._render_qweb_pdf([report_id])[0]
#         pdfhttpheaders = [('Content-Type', 'application/pdf'), ('Content-Length', u'%s' % len(report))]
#         if report_type == 'pdf' and download:
#             filename = "%s.pdf" % (re.sub('\W+', '-', medical_report.partner_id.name))
#             pdfhttpheaders.append(('Content-Disposition', content_disposition(filename)))

#         return request.make_response(report, headers=pdfhttpheaders)

# @http.route(['/?db=<string:db_name>/covid-19/result/<string:public_code>'], type='http', auth='public', website=True,  methods=['GET'])
# def get_medical_lab_result2(self, public_code, db_name):
#     if public_code:
#         medical_report = request.env['test.result'].sudo().search([('public_code', '=', public_code)])
#         print(medical_report)
#         if medical_report:
#             return request.render('medical_lab.medical_test_result_portal_content',
#                                   {'medical_report': medical_report})
#         else:
#             return request.render('http_routing.404')
#     else:
#         return request.render('http_routing.404')
