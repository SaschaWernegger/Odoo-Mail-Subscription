from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

from ..policies import get_policy


class BulkSubscriptionWizard(models.TransientModel):
    _name = 'bulk.subscription.wizard'
    _description = 'Bulk Manage Template Subscriptions'

    template_id = fields.Many2one('mail.template')
    user_ids = fields.Many2many('res.users')
    action = fields.Selection([
        ('subscribe', 'Subscribe All'),
        ('unsubscribe', 'Unsubscribe All'),
    ])

    def action_apply(self):
        """Apply bulk subscription changes.
        
        - Enable: Marks selected users as subscribed
        - Disable: Marks selected users as unsubscribed
        """
        self.ensure_one()

        template = self.template_id
        if not template.subscription_policy_id:
            raise ValidationError(_("Template has no subscription policy."))

        policy_name = template.subscription_policy_id.name
        policy = get_policy(policy_name)
        if not policy:
            raise ValidationError(_("Unsupported subscription policy for bulk update."))

        if policy_name not in ('marketing', 'informational'):
            raise ValidationError(_("Unsupported subscription policy for bulk update."))

        subscription_model = self.env['user.mail.subscription'].sudo()

        users = self.user_ids
        if not users:
            raise ValidationError(_("Please select at least one user."))

        existing = subscription_model.search([
            ('template_id', '=', template.id),
            ('user_id', 'in', users.ids),
        ])
        target_state = self.action == 'subscribe'
        existing.write({'is_subscribed': target_state})

        existing_user_ids = set(existing.mapped('user_id').ids)
        to_create = []
        for user in users:
            if user.id in existing_user_ids:
                continue
            to_create.append({
                'user_id': user.id,
                'template_id': template.id,
                'is_subscribed': target_state,
            })

        if to_create:
            subscription_model.create(to_create)

        return {'type': 'ir.actions.act_window_close'}
