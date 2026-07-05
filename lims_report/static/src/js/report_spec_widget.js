/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Dialog } from "@web/core/dialog/dialog";
import { _t } from "@web/core/l10n/translation";
import { Component, useState, onWillStart } from "@odoo/owl";

// ── Live specification preview (mirrors server _get_specification_text logic) ─
function previewSpec(state) {
    const lt = state.limitType;
    const parts = [];
    if (lt === "mrl") {
        if (state.mrl > 0) parts.push(`≤ ${state.mrl}`);
    } else if (lt === "max") {
        if (state.maxValue > 0) parts.push(`≤ ${state.maxValue}`);
    } else if (lt === "range") {
        if (state.minValue > 0 && state.maxValue > 0)
            parts.push(`${state.minValue} – ${state.maxValue}`);
        else if (state.maxValue > 0) parts.push(`≤ ${state.maxValue}`);
        else if (state.minValue > 0) parts.push(`≥ ${state.minValue}`);
    }
    const uom = state.uoms.find((u) => u.id === state.uomId);
    if (uom) parts.push(uom.name);
    const reg = state.regulations.find((r) => r.id === state.regulationId);
    if (reg) parts.push(`(${reg.name})`);
    return parts.join(" ") || "—";
}

// ─────────────────────────────────────────────────────────────────────────────
//  ReportSpecFixDialog — rich 3-mode dialog: Switch | Edit | Create
// ─────────────────────────────────────────────────────────────────────────────
class ReportSpecFixDialog extends Component {
    static template = "lims_report.ReportSpecFixDialog";
    static components = { Dialog };
    static props = {
        analysisId: Number,
        close:      Function,
        onSaved:    Function,
    };

    setup() {
        this.orm          = useService("orm");
        this.notification = useService("notification");

        this.state = useState({
            loading:    true,
            saving:     false,
            // context
            analyteName:         "",
            instrumentName:      "",
            sampleCategoryName:  "",
            sampleTypeName:      "",
            // tab: 'switch' | 'edit' | 'create'
            tab:        "edit",
            // switch tab
            availableLimits: [],
            switchToId:      false,
            // edit/create shared fields
            uoms:            [],
            regulations:     [],
            limitType:       "mrl",
            mrl:             0,
            minValue:        0,
            maxValue:        0,
            regulationId:    false,
            uomId:           false,
            // spec override (always editable)
            specificationOverride: "",
        });

        onWillStart(() => this._load());
    }

    async _load() {
        try {
            const data = await this.orm.call(
                "lims.analysis", "get_report_limit_data", [[this.props.analysisId]]
            );
            this.state.analyteName         = data.analyte_name;
            this.state.instrumentName      = data.instrument_name || "";
            this.state.sampleCategoryName  = data.sample_category_name || "";
            this.state.sampleTypeName      = data.sample_type_name || "";
            this.state.availableLimits     = data.available_limits;
            this.state.uoms                = data.uoms;
            this.state.regulations         = data.regulations;
            this.state.specificationOverride = data.specification || "";

            const cl = data.current_limit;
            if (cl) {
                this._applyLimit(cl);
                this.state.tab = "edit";
            } else {
                this.state.tab = data.available_limits.length ? "switch" : "create";
            }
            if (data.available_limits.length) {
                this.state.switchToId = data.available_limits[0].id;
            }
        } catch (e) {
            this.notification.add(_t("Failed to load limit data."), { type: "danger" });
        } finally {
            this.state.loading = false;
        }
    }

    _applyLimit(l) {
        this.state.limitType    = l.limit_type || "mrl";
        this.state.mrl          = l.mrl || 0;
        this.state.minValue     = l.min_value || 0;
        this.state.maxValue     = l.max_value || 0;
        this.state.regulationId = l.regulation_id || false;
        this.state.uomId        = l.uom_id || false;
    }

    // ── Computed ─────────────────────────────────────────────────────────────
    get specPreview() { return previewSpec(this.state); }

    get hasExistingLimit() {
        // True when opening in edit mode (server sent a current_limit)
        return this.state.tab === "edit";
    }

    // ── Event handlers ───────────────────────────────────────────────────────
    setTab = (tab) => { this.state.tab = tab; };

    onSwitchLimitChange = (ev) => {
        const id = parseInt(ev.target.value) || false;
        this.state.switchToId = id;
        const found = this.state.availableLimits.find((l) => l.id === id);
        if (found) this._applyLimit(found);
    };

    onLimitTypeChange  = (ev) => { this.state.limitType    = ev.target.value; };
    onMrlInput         = (ev) => { this.state.mrl          = parseFloat(ev.target.value) || 0; };
    onMinInput         = (ev) => { this.state.minValue     = parseFloat(ev.target.value) || 0; };
    onMaxInput         = (ev) => { this.state.maxValue     = parseFloat(ev.target.value) || 0; };
    onRegulationChange = (ev) => { this.state.regulationId = parseInt(ev.target.value) || false; };
    onUomChange        = (ev) => { this.state.uomId        = parseInt(ev.target.value) || false; };
    onSpecInput        = (ev) => { this.state.specificationOverride = ev.target.value; };

    // ── Save ─────────────────────────────────────────────────────────────────
    onSaveClick = async () => {
        this.state.saving = true;
        try {
            const vals = {
                mode:                   this.state.tab,
                limit_id:               this.state.switchToId,
                limit_type:             this.state.limitType,
                mrl:                    this.state.mrl,
                min_value:              this.state.minValue,
                max_value:              this.state.maxValue,
                regulation_id:          this.state.regulationId,
                uom_id:                 this.state.uomId,
                specification_override: this.state.specificationOverride,
            };
            const result = await this.orm.call(
                "lims.analysis", "save_report_limit", [[this.props.analysisId], vals]
            );
            this.props.onSaved(result);
            this.notification.add(_t("Saved successfully."), { type: "success" });
            this.props.close();
        } catch (e) {
            this.notification.add(
                _t("Save failed: ") + (e.message || String(e)),
                { type: "danger" }
            );
        } finally {
            this.state.saving = false;
        }
    };

    onCancelClick = () => this.props.close();
}

// ─────────────────────────────────────────────────────────────────────────────
//  ReportSpecWidget — field widget for `specification` in the analysis list
//  Shows: spec text (inline editable) + limit badge + fix button
// ─────────────────────────────────────────────────────────────────────────────
export class ReportSpecWidget extends Component {
    static template = "lims_report.ReportSpecWidget";
    static components = { ReportSpecFixDialog };
    static props = ["record", "name", "readonly", "*"];

    setup() {
        this.orm           = useService("orm");
        this.dialogService = useService("dialog");
        this.notification  = useService("notification");

        this.state = useState({
            editingSpec:  false,
            draftSpec:    "",
            saving:       false,
            // local cache of spec/limit shown after dialog save
            localSpec:    null,
            localLimitName: null,
        });
    }

    get analysisId()  { return this.props.record.resId; }
    get isReadonly()  { return !!this.props.readonly; }

    get displaySpec() {
        if (this.state.localSpec !== null) return this.state.localSpec;
        return this.props.record.data[this.props.name] || "";
    }

    get limitName() {
        if (this.state.localLimitName !== null) return this.state.localLimitName;
        const limitField = this.props.record.data["limit_id"];
        if (!limitField) return "";
        if (Array.isArray(limitField)) return limitField[1] || "";
        return "";
    }

    // ── Inline spec editing ──────────────────────────────────────────────────
    startEditSpec = () => {
        if (this.isReadonly) return;
        this.state.draftSpec    = this.displaySpec;
        this.state.editingSpec  = true;
    };

    onSpecInput = (ev) => { this.state.draftSpec = ev.target.value; };

    onSpecKeydown = async (ev) => {
        if (ev.key === "Enter")  { ev.preventDefault(); await this._commitSpec(); }
        if (ev.key === "Escape") { this.state.editingSpec = false; }
    };

    onSpecBlur = async () => { await this._commitSpec(); };

    async _commitSpec() {
        if (!this.state.editingSpec) return;
        const val = this.state.draftSpec;
        this.state.editingSpec = false;
        this.state.saving      = true;
        try {
            await this.orm.write("lims.analysis", [this.analysisId], { specification: val });
            this.state.localSpec = val;
        } catch (e) {
            this.notification.add(
                _t("Save failed: ") + (e.message || String(e)),
                { type: "danger" }
            );
        } finally {
            this.state.saving = false;
        }
    }

    // ── Fix dialog ───────────────────────────────────────────────────────────
    openDialog = () => {
        if (!this.analysisId) return;
        this.dialogService.add(ReportSpecFixDialog, {
            analysisId: this.analysisId,
            onSaved: (result) => {
                this.state.localSpec      = result.specification;
                this.state.localLimitName = result.limit_name;
            },
        });
    };
}

// ── Field registry ────────────────────────────────────────────────────────────
registry.category("fields").add("report_spec_widget", {
    component: ReportSpecWidget,
    displayName: "Report Spec Widget",
    supportedTypes: ["char"],
    extractProps({ attrs, field }, dynamicInfo) {
        return {};
    },
});
