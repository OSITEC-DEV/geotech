# -*- coding: utf-8 -*-
import logging
import time

from odoo import models
from odoo.http import request

_logger = logging.getLogger(__name__)

# Paths that must always stay reachable, blocked or not, so an administrator
# can always log in and upload a renewed license, and so static assets /
# session plumbing never gets caught by the redirect below.
_ALWAYS_ALLOWED_PREFIXES = (
    '/web/login',
    '/web/session',
    '/web/webclient',
    '/web/binary',
    '/web/static',
    '/web/assets',
    '/website',
    '/longpolling',
    '/bus',
    '/lims_license',
)

# Per-worker-process cache so _dispatch doesn't hit the database on every
# single request. The daily cron and every license upload still recompute
# authoritatively; this only bounds how stale a worker's view can get.
_STATUS_CACHE_TTL = 60
_status_cache = {'value': None, 'ts': 0.0}


def _get_cached_status(env):
    now = time.monotonic()
    if _status_cache['value'] is None or (now - _status_cache['ts']) > _STATUS_CACHE_TTL:
        _status_cache['value'] = env['lims.license'].sudo().get_status()
        _status_cache['ts'] = now
    return _status_cache['value']


class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    def session_info(self):
        result = super().session_info()
        try:
            result['lims_license_status'] = _get_cached_status(self.env)
        except Exception:
            _logger.exception('lims_license: session_info status check failed, failing open')
            result['lims_license_status'] = {'state': 'valid', 'blocked': False, 'message': False}
        return result

    @classmethod
    def _dispatch(cls, endpoint):
        request_path = request.httprequest.path
        if any(request_path.startswith(p) for p in _ALWAYS_ALLOWED_PREFIXES):
            return super()._dispatch(endpoint)

        try:
            status = _get_cached_status(request.env)
        except Exception:
            # A bug or unexpected state in the license check must never turn
            # into a customer-facing outage - fail open, log loudly instead.
            _logger.exception('lims_license: dispatch status check failed, failing open')
            return super()._dispatch(endpoint)

        if status.get('blocked'):
            user = request.env.user
            is_admin = user and not user._is_public() and user.has_group('base.group_system')
            if not is_admin:
                return request.redirect('/lims_license/blocked')

        return super()._dispatch(endpoint)
