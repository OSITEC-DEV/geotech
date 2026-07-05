from odoo import models, fields, api, _


class LimsSampleUnlockWizard(models.TransientModel):
    _name = "lims.sample.unlock.wizard"
    _description = "Unlock Sample Wizard"

    reason = fields.Char(string="Unlock Reason", required=True)
    user_id = fields.Many2one("res.users", "Requested by")
    request_ids = fields.Many2many("lims.sample.main")
    sample_ids = fields.Many2many("lims.sample.preparation")

    def _prepare_unlock_vals(self):
        user_name = self.user_id.name
        # concatenate reason + user
        final_reason = f"{self.reason} | Unlocked for: {user_name} | By: {self.env.user.name}"
        return {
            "unlock_datetime": fields.Datetime.now(),
            "unlock_reason": final_reason,
            "lock": False
        }

    def action_confirm_unlock(self):
        self.ensure_one()

        if self.request_ids:
            for req in self.request_ids:
                req.write(self._prepare_unlock_vals())
                for line in req.sample_line:
                    line.lock = False
                for line in req.sample_line_prepared:
                    line.lock = False
        elif self.sample_ids:
            for sample in self.sample_ids:
                sample.write(self._prepare_unlock_vals())

        else:
            return

        return {"type": "ir.actions.act_window_close"}
