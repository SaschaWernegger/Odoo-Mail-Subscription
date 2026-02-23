/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { ListController } from "@web/views/list/list_controller";

patch(ListController.prototype, {
    async onRecordSaved(record) {
        await super.onRecordSaved(record);
        if (this.props.resModel === "my.mail.subscription.sql.view") {
            await this.model.load();
        }
    },
});
