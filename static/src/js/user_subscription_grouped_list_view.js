/** @odoo-module */

import { onMounted, onPatched } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { X2ManyField, x2ManyField } from "@web/views/fields/x2many/x2many_field";
import { ListRenderer } from "@web/views/list/list_renderer";

class GroupedInlineListRenderer extends ListRenderer {
    setup() {
        super.setup(...arguments);
        onMounted(() => this._scheduleInlineGrouping());
        onPatched(() => this._scheduleInlineGrouping());
    }

    _scheduleInlineGrouping() {
        requestAnimationFrame(() => this._applyInlineGrouping());
    }

    _applyInlineGrouping() {
        const table = this.tableRef?.el;
        if (!table) {
            return;
        }

        const container = table.closest(
            [
                '.o_field_x2many[name="user_mail_subscription_ids"]',
                '.o_field_x2many[data-name="user_mail_subscription_ids"]',
                '.o_field_widget[name="user_mail_subscription_ids"]',
                '.o_field_widget[data-name="user_mail_subscription_ids"]',
            ].join(",")
        );
        if (!container || !table.closest(".o_form_view")) {
            return;
        }

        const body = table.querySelector("tbody");
        if (!body) {
            return;
        }

        for (const oldRow of body.querySelectorAll("tr.o_my_mail_group_row")) {
            oldRow.remove();
        }

        const rows = Array.from(body.querySelectorAll("tr.o_data_row"));
        if (!rows.length) {
            return;
        }

        const records = this.props.list?.records || [];
        const recordById = new Map(records.map((record) => [record.id, record]));

        let previousLabel = null;
        let currentGroupKey = null;
        rows.forEach((row, index) => {
            const rowKey = row.dataset.id || "";
            const record = recordById.get(rowKey) || records[index];
            const templateGroupLabel = (record?.data?.template_group_label || "").trim();
            const policyLabel = (record?.data?.subscription_policy_label || "").trim();
            const label = templateGroupLabel || policyLabel || "Other";
            const groupKey = this._slugify(label);

            if (label === previousLabel) {
                if (currentGroupKey) {
                    row.dataset.groupKey = currentGroupKey;
                }
                return;
            }
            previousLabel = label;
            currentGroupKey = groupKey;

            const groupRow = document.createElement("tr");
            groupRow.className = "o_my_mail_group_row";
            groupRow.dataset.groupKey = groupKey;
            groupRow.dataset.groupCollapsed = "false";
            groupRow.setAttribute("role", "button");
            groupRow.setAttribute("aria-expanded", "true");
            groupRow.addEventListener("click", (event) => {
                event.preventDefault();
                this._toggleGroup(groupRow, body);
            });

            const cell = document.createElement("td");
            cell.colSpan = row.children.length || 1;
            cell.innerHTML = `
                <span class="o_my_mail_group_toggle" aria-hidden="true"></span>
                <span class="o_my_mail_group_label">${this._escapeHtml(label)}</span>
            `;

            groupRow.appendChild(cell);
            row.before(groupRow);
            row.dataset.groupKey = groupKey;
        });
    }

    _toggleGroup(groupRow, body) {
        const groupKey = groupRow.dataset.groupKey;
        const isCollapsed = groupRow.dataset.groupCollapsed === "true";
        groupRow.dataset.groupCollapsed = isCollapsed ? "false" : "true";
        groupRow.setAttribute("aria-expanded", isCollapsed ? "true" : "false");

        const rows = Array.from(body.querySelectorAll("tr.o_data_row"));
        rows.forEach((row) => {
            if (row.dataset.groupKey !== groupKey) {
                return;
            }
            row.classList.toggle("o_my_mail_group_row_hidden", !isCollapsed);
        });
    }

    _slugify(value) {
        return value.toLowerCase().replace(/\s+/g, "-").replace(/[^a-z0-9\-]/g, "");
    }

    _escapeHtml(value) {
        const temp = document.createElement("div");
        temp.textContent = value;
        return temp.innerHTML;
    }
}

class GroupedX2ManyField extends X2ManyField {}

GroupedX2ManyField.components = {
    ...X2ManyField.components,
    ListRenderer: GroupedInlineListRenderer,
};

const groupedX2ManyField = {
    ...x2ManyField,
    component: GroupedX2ManyField,
};

registry.category("fields").add("my_mail_grouped_x2many", groupedX2ManyField);
registry.category("fields").add("form.my_mail_grouped_x2many", groupedX2ManyField);
