import json
import logging
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

class LimsAPIController(http.Controller):

    @http.route("/api/lims/analysis/JSON/upload", type="json", auth="public", methods=["POST","GET"], csrf=False)
    def update_lims_analysis(self, **post):
        _logger.info("IM HERE API")
        try:
            # Extract JSON payload
            json_data = request.jsonrequest
            # Validate required fields
            sample_code = json_data.get("sample_code")
            if not sample_code:
                return {"status": "error", "message": "Missing sample_code"}

            # Search for the lims.analysis record by sample_code
            analysis = request.env["lims.analysis"].sudo().search([("sample_code", "=", sample_code)], limit=1)

            if not analysis:
                return {"status": "error", "message": f"No record found for sample_code: {sample_code}"}

            # Update the json_data field
            analysis.sudo().write({"json_report": json_data})

            return {"status": "success", "message": f"Record {analysis.name} updated successfully"}

        except Exception as e:
            _logger.error(f"Error updating LIMS Analysis: {str(e)}")
            return {"status": "error", "message": str(e)}
