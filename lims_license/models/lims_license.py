# -*- coding: utf-8 -*-
import base64
import json
import logging

from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)

try:
    from cryptography.hazmat.primitives import serialization
    from cryptography.exceptions import InvalidSignature
except ImportError:  # pragma: no cover
    serialization = None
    InvalidSignature = Exception
    _logger.warning(
        "The 'cryptography' python package is not installed. "
        "lims_license cannot validate any license until it is (pip install cryptography)."
    )

# Public keys the validator trusts, keyed by the license payload's "key_version".
# Only the PUBLIC key ever lives here. The matching private key lives in the
# separate, private license-generator tool and must never be committed here.
# To rotate keys: generate a new keypair, add its version below, keep the old
# entry until every issued license using it has been re-issued/expired.
_PUBLIC_KEY_PEMS = {
    1: """-----BEGIN PUBLIC KEY-----
MCowBQYDK2VwAyEAwCIr7cbgPVwONiYevwoH/DWcxRNf5HykBbuZZwpGTaI=
-----END PUBLIC KEY-----""",
}

# Days of soft-warning grace when NO license has ever been configured at all
# (e.g. right after a fresh install, before the vendor has issued one yet).
_BOOTSTRAP_GRACE_DAYS = 30

_PROBLEM_SINCE_PARAM = 'lims_license.problem_since'


def _canonical_payload_bytes(payload: dict) -> bytes:
    """Must stay byte-identical to license_format.canonical_payload_bytes()
    in the private lims-licensing generator tool, or every signature check
    below will fail."""
    return json.dumps(payload, sort_keys=True, separators=(',', ':')).encode('utf-8')


class LimsLicense(models.Model):
    _name = 'lims.license'
    _description = 'LIMS License'
    _inherit = ['mail.thread']
    _order = 'create_date desc'

    name = fields.Char('Reference', default='New', copy=False, index=True)
    license_file = fields.Binary('License File (.lic)', required=True, attachment=True)
    license_filename = fields.Char('Filename')
    is_current = fields.Boolean('Currently Active', default=False, copy=False, tracking=True)

    valid_signature = fields.Boolean('Signature Valid', readonly=True, copy=False)
    db_uuid_match = fields.Boolean('Matches This Database', readonly=True, copy=False)
    error_message = fields.Text('Validation Error', readonly=True, copy=False)

    customer = fields.Char('Licensed To', readonly=True, copy=False)
    modules_licensed = fields.Char('Licensed Modules', readonly=True, copy=False)
    seats = fields.Integer('Seats (0 = unlimited)', readonly=True, copy=False)
    issued_date = fields.Date('Issued', readonly=True, copy=False)
    expiry_date = fields.Date('Expires (empty = perpetual)', readonly=True, copy=False)
    grace_days = fields.Integer('Grace Period (days)', readonly=True, copy=False, default=14)
    key_version = fields.Integer('Key Version', readonly=True, copy=False)

    last_checked = fields.Datetime('Last Checked', readonly=True, copy=False)
    current_db_uuid = fields.Char('This Database UUID', compute='_compute_current_db_uuid',
                                  help='Send this to the vendor when requesting or renewing a license.')

    @api.depends()
    def _compute_current_db_uuid(self):
        db_uuid = self.env['ir.config_parameter'].sudo().get_param('database.uuid')
        for record in self:
            record.current_db_uuid = db_uuid

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('lims.license') or 'New'
        records = super().create(vals_list)
        records._validate_and_activate()
        return records

    def write(self, vals):
        res = super().write(vals)
        if 'license_file' in vals:
            self._validate_and_activate()
        return res

    def _validate_and_activate(self):
        """Parse + verify the uploaded file, populate fields, and if it
        validates cleanly, make it the single active license."""
        for record in self:
            ok, fields_values, error = record._parse_and_verify()
            fields_values.update({
                'valid_signature': ok,
                'error_message': error or False,
                'last_checked': fields.Datetime.now(),
            })
            super(LimsLicense, record).write(fields_values)
            if ok and fields_values.get('db_uuid_match'):
                other = self.search([('id', '!=', record.id)])
                other.write({'is_current': False})
                super(LimsLicense, record).write({'is_current': True})
                record.message_post(body=_('License validated and activated.'))
            else:
                record.write({'is_current': False})
                record.message_post(body=_('License validation failed: %s') % (error or _('unknown error')))
        self.env['lims.license']._recompute_problem_status()

    def _parse_and_verify(self):
        """Returns (ok: bool, values: dict of parsed license fields, error: str|None)."""
        self.ensure_one()
        empty_values = {
            'db_uuid_match': False, 'customer': False, 'modules_licensed': False,
            'seats': 0, 'issued_date': False, 'expiry_date': False,
            'grace_days': 14, 'key_version': False,
        }
        if serialization is None:
            return False, empty_values, _("The 'cryptography' python package is not installed on this server.")
        if not self.license_file:
            return False, empty_values, _('No license file uploaded.')

        try:
            raw = base64.b64decode(self.license_file)
            doc = json.loads(raw.decode('utf-8'))
            payload = doc['payload']
            signature = base64.b64decode(doc['signature'])
        except Exception as e:
            return False, empty_values, _('Could not parse license file: %s') % e

        key_version = payload.get('key_version')
        key_pem = _PUBLIC_KEY_PEMS.get(key_version)
        if not key_pem:
            return False, empty_values, _('Unknown key version %s - this license was not issued for this software version.') % key_version

        try:
            public_key = serialization.load_pem_public_key(key_pem.encode('utf-8'))
            public_key.verify(signature, _canonical_payload_bytes(payload))
        except InvalidSignature:
            return False, empty_values, _('Signature verification failed - the license file is invalid or has been tampered with.')
        except Exception as e:
            return False, empty_values, _('Signature verification error: %s') % e

        db_uuid = self.env['ir.config_parameter'].sudo().get_param('database.uuid')
        db_uuid_match = payload.get('db_uuid') == db_uuid

        values = {
            'customer': payload.get('customer'),
            'modules_licensed': ', '.join(payload.get('modules', [])),
            'seats': payload.get('seats') or 0,
            'issued_date': payload.get('issued'),
            'expiry_date': payload.get('expires') or False,
            'grace_days': payload.get('grace_days', 14),
            'key_version': key_version,
            'db_uuid_match': db_uuid_match,
        }
        if not db_uuid_match:
            return False, values, _(
                'This license was issued for a different database (license db_uuid=%s, this database=%s).'
            ) % (payload.get('db_uuid'), db_uuid)

        return True, values, None

    # ------------------------------------------------------------------
    # Status / enforcement
    # ------------------------------------------------------------------
    @api.model
    def _get_current(self):
        return self.search([('is_current', '=', True)], limit=1)

    @api.model
    def _recompute_problem_status(self):
        """Re-derive whether there is currently a licensing problem, track
        since when (via ir.config_parameter, independent of any record so it
        works even before any license has ever been uploaded), and return the
        effective status dict. Called by the cron and after every upload."""
        icp = self.env['ir.config_parameter'].sudo()
        current = self._get_current()
        today = fields.Date.context_today(self)

        is_problem = True
        reason = _('No license has been configured for this instance yet.')
        grace_days = _BOOTSTRAP_GRACE_DAYS

        if current:
            grace_days = current.grace_days or 14
            if not current.valid_signature or not current.db_uuid_match:
                reason = current.error_message or _('The current license is invalid.')
            elif current.expiry_date and current.expiry_date < today:
                reason = _('The license expired on %s.') % current.expiry_date
            else:
                is_problem = False
                reason = False

        problem_since_str = icp.get_param(_PROBLEM_SINCE_PARAM)
        if is_problem and not problem_since_str:
            icp.set_param(_PROBLEM_SINCE_PARAM, today.isoformat())
            problem_since_str = today.isoformat()
        elif not is_problem and problem_since_str:
            icp.set_param(_PROBLEM_SINCE_PARAM, '')
            problem_since_str = None

        if not is_problem:
            return {'state': 'valid', 'blocked': False, 'message': False}

        problem_since = fields.Date.from_string(problem_since_str) if problem_since_str else today
        days_in_problem = (today - problem_since).days
        if days_in_problem <= grace_days:
            days_left = grace_days - days_in_problem
            return {
                'state': 'grace',
                'blocked': False,
                'message': _('%s This system will be restricted to administrators in %d day(s) unless a valid license is uploaded.') % (reason, days_left),
            }
        return {
            'state': 'blocked',
            'blocked': True,
            'message': _('%s The grace period has ended - non-administrator access is now restricted until a valid license is uploaded.') % reason,
        }

    @api.model
    def get_status(self):
        """Cheap-ish status accessor for ir.http / templates. Not cached at
        this layer - callers (e.g. ir_http) are expected to add their own
        short-lived caching if called on every request."""
        return self._recompute_problem_status()

    def action_check_now(self):
        self._recompute_problem_status()
        return True
