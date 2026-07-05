/** @odoo-module **/
// NOTE: this is the one piece of lims_license that could not be verified
// against a live Odoo instance in the environment this was written in.
// The registration pattern below (registry.category("main_components"),
// reading `session.lims_license_status`) matches the standard Odoo 17/18
// extension point used for similar global nags, but double-check it renders
// after installing - if it silently doesn't, the underlying data is still
// reliably available via session_info (see models/ir_http.py) and this file
// is the only thing that needs adjusting.

import { registry } from "@web/core/registry";
import { session } from "@web/session";
import { Component, xml } from "@odoo/owl";

class LimsLicenseBanner extends Component {
    static template = xml`
        <div t-if="status and status.state === 'grace'" class="lims_license_banner">
            <t t-esc="status.message"/>
        </div>`;

    get status() {
        return session.lims_license_status;
    }
}

registry.category("main_components").add("LimsLicenseBanner", {
    Component: LimsLicenseBanner,
});
