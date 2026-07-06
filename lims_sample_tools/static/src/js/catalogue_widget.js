/** @odoo-module **/

import { Component, useState, useEffect, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Dialog } from "@web/core/dialog/dialog";

class TestCatalogueDialog extends Component {
    static template = "lims_sample_tools.TestCatalogueDialog";
    static components = { Dialog };
    static props = {
        allProducts: Array,
        packIds: Object,
        childToPackMap: Object,
        allChildIds: Object,
        departments: Array,
        currentProductIds: Array,
        testUnits: { type: Object, optional: true },
        subcontracting: { type: Object, optional: true },
        onSave: Function,
        close: Function,
    };

    setup() {
        const existingSub = this.props.subcontracting || {};
        const externalFlags = {};
        for (const [k, v] of Object.entries(existingSub)) {
            if (v) externalFlags[k] = true;
        }
        this.state = useState({
            search: "",
            expandedPacks: {},
            expandedCategories: {},
            selectedIds: new Set(this.props.currentProductIds.map(String)),
            units: { ...(this.props.testUnits || {}) },
            subcontracting: { ...existingSub },
            externalFlags,
        });
    }

    get filteredProducts() {
        const q = this.state.search.toLowerCase().trim();
        if (!q) return this.props.allProducts;
        return this.props.allProducts.filter(p =>
            p.display_name.toLowerCase().includes(q) ||
            (p.categ_name || "").toLowerCase().includes(q)
        );
    }

    get packs() {
        return this.filteredProducts.filter(p => p.isPack && (p.child_ids || []).length > 0);
    }

    get individuals() {
        return this.filteredProducts.filter(p =>
            p.isParameter &&
            !p.isPack &&
            !this.props.allChildIds.has(String(p.id))
        );
    }

    get categories() {
        const map = {};
        for (const p of this.individuals) {
            const key = p.categ_id || 0;
            if (!map[key]) {
                map[key] = { id: key, name: p.categ_name || "Uncategorized", products: [] };
            }
            map[key].products.push(p);
        }
        return Object.values(map).sort((a, b) => a.name.localeCompare(b.name));
    }

    isPack(id) {
        return this.props.packIds.has(String(id));
    }

    isSelected(id) {
        return this.state.selectedIds.has(String(id));
    }

    isCategoryExpanded(catId) {
        return this.state.expandedCategories[catId] !== false;
    }

    isPackExpanded(packId) {
        return !!this.state.expandedPacks[packId];
    }

    isPackChild(id) {
        return this.props.allChildIds.has(String(id));
    }

    getUnit(id) {
        return this.state.units[String(id)] ?? 1;
    }

    getDeptId(id) {
        return this.state.subcontracting[String(id)] ?? "";
    }

    get selectedCount() {
        return this.state.selectedIds.size;
    }

    toggleCategory(catId) {
        this.state.expandedCategories[catId] = !this.isCategoryExpanded(catId);
    }

    togglePack(packId) {
        this.state.expandedPacks[packId] = !this.isPackExpanded(packId);
    }

    selectPack(pack) {
        const key = String(pack.id);
        const children = pack.child_ids || [];

        if (this.isPackAllSelected(pack)) {
            this.state.selectedIds.delete(key);
            delete this.state.units[key];
            delete this.state.subcontracting[key];
            delete this.state.externalFlags[key];
            children.forEach(c => {
                this.state.selectedIds.delete(String(c.id));
                delete this.state.units[String(c.id)];
                delete this.state.subcontracting[String(c.id)];
                delete this.state.externalFlags[String(c.id)];
            });
        } else {
            this.state.selectedIds.add(key);
            this.state.units[key] = 1;
            this._applySubcontractDefault(key, pack);
            children.forEach(c => {
                this.state.selectedIds.delete(String(c.id));
                delete this.state.units[String(c.id)];
                delete this.state.subcontracting[String(c.id)];
                delete this.state.externalFlags[String(c.id)];
            });
        }
        this.state.selectedIds = new Set(this.state.selectedIds);
    }

    _findProduct(id) {
        const direct = this.props.allProducts.find(p => p.id === id);
        if (direct) return direct;
        for (const p of this.props.allProducts) {
            if (p.isPack) {
                const child = (p.child_ids || []).find(c => c.id === id);
                if (child) return child;
            }
        }
        return null;
    }

    _applySubcontractDefault(key, product) {
        if (product?.is_subcontract) {
            this.state.externalFlags[key] = true;
            if (!this.state.subcontracting[key] && this.props.departments.length) {
                this.state.subcontracting[key] = this.props.departments[0].id;
            }
        }
    }

    isExternal(id) {
        return !!this.state.externalFlags[String(id)];
    }

    setExternalFlag(id, ev) {
        const key = String(id);
        if (ev.target.value === "external") {
            this.state.externalFlags[key] = true;
            if (!this.state.subcontracting[key] && this.props.departments.length) {
                this.state.subcontracting[key] = this.props.departments[0].id;
            }
        } else {
            delete this.state.externalFlags[key];
            delete this.state.subcontracting[key];
        }
    }

    toggleProduct(id) {
        const key = String(id);

        if (this.state.selectedIds.has(key)) {
            this.state.selectedIds.delete(key);
            delete this.state.units[key];
            delete this.state.subcontracting[key];
            delete this.state.externalFlags[key];
        } else {
            this.state.selectedIds.add(key);
            this.state.units[key] = 1;
            this._applySubcontractDefault(key, this._findProduct(id));

            const parentPackId = this.props.childToPackMap[key];
            if (parentPackId && this.state.selectedIds.has(parentPackId)) {
                this.state.selectedIds.delete(parentPackId);
                delete this.state.units[parentPackId];
                delete this.state.subcontracting[parentPackId];
                delete this.state.externalFlags[parentPackId];
            }
        }
        this.state.selectedIds = new Set(this.state.selectedIds);
    }

    isPackAllSelected(pack) {
        const packId = String(pack.id);
        if (this.state.selectedIds.has(packId)) {
            return true;
        }
        const children = pack.child_ids || [];
        return (
            children.length > 0 &&
            children.every(c => this.isSelected(c.id))
        );
    }

    isPackPartialSelected(pack) {
        const children = pack.child_ids || [];
        const count = children.filter(c => this.isSelected(c.id)).length;
        return count > 0 && count < children.length;
    }

    isPackFullChildrenSelected(pack) {
        const children = pack.child_ids || [];
        return children.length > 0 && children.every(c => this.isSelected(c.id));
    }

    setUnit(id, ev) {
        const val = parseInt(ev.target.value, 10);
        this.state.units[String(id)] = isNaN(val) || val < 1 ? 1 : val;
    }

    setDept(id, ev) {
        const val = parseInt(ev.target.value, 10);
        if (isNaN(val)) {
            delete this.state.subcontracting[String(id)];
        } else {
            this.state.subcontracting[String(id)] = val;
        }
    }

    save() {
        const cleanUnits = {};
        const cleanSub = {};
        for (const id of this.state.selectedIds) {
            cleanUnits[id] = this.state.units[id] ?? 1;
            if (this.state.subcontracting[id]) {
                cleanSub[id] = this.state.subcontracting[id];
            }
        }
        this.props.onSave({
            productIds: Array.from(this.state.selectedIds).map(Number),
            testUnits: cleanUnits,
            subcontracting: cleanSub,
        });
        this.props.close();
    }
}

class TestCatalogueWidget extends Component {
    static template = "lims_sample_tools.TestCatalogueWidget";
    static components = {};
    static props = {
        id: { type: String, optional: true },
        record: Object,
        name: String,
        readonly: { type: Boolean, optional: true },
    };

    setup() {
        this.dialogService = useService("dialog");
        this.orm = useService("orm");
        this.state = useState({
            allProducts: [],
            departments: [],
            packIds: new Set(),
            allChildIds: new Set(),
            childToPackMap: {},
            loaded: false,
        });

        onWillStart(() => this._fetchCatalogue());

        useEffect(() => {
            this.state.loaded = false;
            this._fetchCatalogue();
        }, () => {
            const cat = this.props.record.data["sample"];
            return [Array.isArray(cat) ? cat[0] : cat];
        });
    }

    async _fetchCatalogue() {
        const catRaw = this.props.record.data["sample"];
        const categoryId = Array.isArray(catRaw) ? catRaw[0] : (catRaw || false);

        if (!categoryId) {
            this.state.allProducts = [];
            this.state.packIds = new Set();
            this.state.allChildIds = new Set();
            this.state.childToPackMap = {};
            this.state.loaded = true;
            return;
        }

        const productDomain = [
            "&",
            ["allowed_sample_type_ids", "in", [categoryId]],
            "|",
            ["isPack", "=", true],
            ["isParameter", "=", true],
        ];

        const [products, departments] = await Promise.all([
            this.orm.searchRead(
                "product.product",
                productDomain,
                [
                    "id", "display_name", "isPack", "isParameter",
                    "categ_id", "child_ids", "is_subcontract",
                ],
                { limit: false }
            ),
            this.orm.searchRead(
                "lims.department",
                [["is_subcontractor", "=", true]],
                ["id", "display_name"]
            ),
        ]);

        const categIds = [...new Set(products.map(p => p.categ_id?.[0]).filter(Boolean))];
        const categMap = {};
        if (categIds.length) {
            const categs = await this.orm.read("product.category", categIds, ["id", "name"]);
            categs.forEach(c => { categMap[c.id] = c.name; });
        }

        const rawChildIds = [
            ...new Set(
                products
                    .filter(p => p.isPack && p.child_ids?.length)
                    .flatMap(p => p.child_ids)
            )
        ];

        const childMap = {};
        if (rawChildIds.length) {
            const children = await this.orm.read(
                "product.product",
                rawChildIds,
                ["id", "display_name", "isParameter", "categ_id", "is_subcontract"]
            );
            children.forEach(c => { childMap[c.id] = c; });
        }

        const childToPackMap = {};
        products
            .filter(p => p.isPack)
            .forEach(pack => {
                (pack.child_ids || []).forEach(cid => {
                    childToPackMap[String(cid)] = String(pack.id);
                });
            });

        const allChildIds = new Set(Object.keys(childToPackMap));

        this.state.allProducts = products.map(p => ({
            ...p,
            isPack: p.isPack || false,
            isParameter: p.isParameter || false,
            categ_id: p.categ_id?.[0] ?? 0,
            categ_name: p.categ_id ? categMap[p.categ_id[0]] : "Uncategorized",
            child_ids: (p.child_ids || []).map(cid => childMap[cid]).filter(Boolean),
        }));

        this.state.packIds = new Set(
            products.filter(p => p.isPack).map(p => String(p.id))
        );
        this.state.allChildIds = allChildIds;
        this.state.childToPackMap = childToPackMap;
        this.state.departments = departments;
        this.state.loaded = true;
    }

    get currentProductIds() {
        const m2m = this.props.record.data["product_ids"];
        if (!m2m) return [];
        if (m2m.currentIds) return m2m.currentIds;
        if (m2m.records) return m2m.records.map(r => r.resId);
        return [];
    }

    get testUnits() {
        const val = this.props.record.data["test_units"];
        return (val && typeof val === "object") ? val : {};
    }

    get subcontracting() {
        const val = this.props.record.data["subcontracting"];
        return (val && typeof val === "object") ? val : {};
    }

    getProductName(productId) {
        const found = this.state.allProducts.find(p => p.id === productId);
        if (found) return found.display_name;
        for (const p of this.state.allProducts) {
            if (p.isPack) {
                const child = (p.child_ids || []).find(c => c.id === productId);
                if (child) return child.display_name;
            }
        }
        return "#" + productId;
    }

    getUnit(productId) {
        return this.testUnits[String(productId)] ?? 1;
    }

    getProductTooltip(productId) {
        const name = this.getProductName(productId);
        const units = this.getUnit(productId);
        return name + " \u2014 " + units + " unit" + (units > 1 ? "s" : "");
    }

    get summary() {
        const count = this.currentProductIds.length;
        if (!count) return "No tests selected";
        return count + " test" + (count > 1 ? "s" : "") + " selected";
    }

    openCatalogue() {
        this.dialogService.add(TestCatalogueDialog, {
            allProducts: this.state.allProducts,
            packIds: this.state.packIds,
            allChildIds: this.state.allChildIds,
            childToPackMap: this.state.childToPackMap,
            departments: this.state.departments,
            currentProductIds: this.currentProductIds,
            testUnits: this.testUnits,
            subcontracting: this.subcontracting,
            onSave: async ({ productIds, testUnits, subcontracting }) => {
                const currentIds = this.currentProductIds;
                const toAdd = productIds.filter(id => !currentIds.includes(id));
                const remaining = currentIds.filter(id => productIds.includes(id));
                // New selections at the top, then previously existing ones
                const orderedIds = [...toAdd, ...remaining];

                await this.props.record.update({
                    product_ids: [[6, 0, orderedIds]],
                    test_units: testUnits || {},
                    subcontracting: subcontracting || {},
                });
            },
        });
    }
}

registry.category("fields").add("lims_sample_tools_catalogue_widget", {
    component: TestCatalogueWidget,
    supportedTypes: ["many2many"],
});