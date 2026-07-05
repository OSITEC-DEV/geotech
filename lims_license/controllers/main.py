# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request

_PAGE_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8"/>
    <title>License Required</title>
    <style>
        body {{ font-family: -apple-system, "Segoe UI", Arial, sans-serif; background:#f5f5f5;
                display:flex; align-items:center; justify-content:center; height:100vh; margin:0; }}
        .box {{ background:#fff; padding:40px; border-radius:8px; max-width:520px;
                box-shadow:0 2px 12px rgba(0,0,0,0.1); text-align:center; }}
        h1 {{ color:#c0392b; font-size:20px; margin-top:0; }}
        p {{ color:#555; line-height:1.5; }}
        a {{ color:#2980b9; }}
    </style>
</head>
<body>
    <div class="box">
        <h1>License Required</h1>
        <p>{message}</p>
        <p>Please contact your system administrator or the software vendor to renew your license.</p>
        <p><a href="/web/login">Administrator login</a></p>
    </div>
</body>
</html>"""


class LimsLicenseController(http.Controller):

    @http.route('/lims_license/blocked', type='http', auth='public', website=False, sitemap=False, csrf=False)
    def license_blocked(self, **kwargs):
        status = request.env['lims.license'].sudo().get_status()
        message = status.get('message') or 'A valid license is required to use this system.'
        html = _PAGE_TEMPLATE.format(message=message)
        return request.make_response(html, headers=[('Content-Type', 'text/html; charset=utf-8')])
