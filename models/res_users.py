from odoo import models, fields, api

from ..policies import get_policy


class ResUsers(models.Model):
    _inherit = 'res.users'

    subscribed_template_count = fields.Integer(
        string='Subscribed Templates',
        compute='_compute_subscribed_template_count',
    )

    user_mail_subscription_ids = fields.One2many(
        'user.mail.subscription',
        'user_id',
        string="User Subscriptions"
    )

    opted_out_template_ids = fields.Many2many(
        'mail.template',
        compute='_compute_opted_out_template_ids',
        string='Opted-Out Email Templates',
        domain="[('is_user_subscribable', '=', True)]",
    )

    # ========== Computed Fields ==========
    @api.depends('user_mail_subscription_ids', 'user_mail_subscription_ids.is_subscribed')
    def _compute_subscribed_template_count(self):
        subscription_model = self.env['user.mail.subscription'].sudo()

        for user in self:
            user.subscribed_template_count = subscription_model.search_count([
                ('user_id', '=', user.id),
                ('is_subscribed', '=', True),
            ])

    @api.depends('user_mail_subscription_ids', 'user_mail_subscription_ids.is_subscribed')
    def _compute_opted_out_template_ids(self):
        subscription_model = self.env['user.mail.subscription'].sudo()
        for user in self:
            subscriptions = subscription_model.search([
                ('user_id', '=', user.id),
                ('is_subscribed', '=', False),
                ('template_id.is_user_subscribable', '=', True),
            ])
            user.opted_out_template_ids = [(6, 0, subscriptions.mapped('template_id').ids)]

    def action_open_user_mail_subscriptions(self):
        """Open dedicated user subscription list for this user."""
        self.ensure_one()
        return {
            'name': f"Subscriptions: {self.name}",
            'type': 'ir.actions.act_window',
            'res_model': 'user.mail.subscription',
            'view_mode': 'list,form',
            'target': 'current',
            'domain': [('user_id', '=', self.id)],
            'context': {
                'default_user_id': self.id,
                'group_by': 'template_group_label',
                'from_user_view': True,
            },
        }

    def _ensure_subscriptions_for_templates(self):
        """Create missing subscription records for non-transactional templates."""
        self.ensure_one()

        template_model = self.env['mail.template'].sudo()
        subscription_model = self.env['user.mail.subscription'].sudo()

        templates = template_model.search([
            ('subscription_policy_id', '!=', False),
            ('subscription_policy_id.name', '!=', 'transactional'),
            ('is_user_subscribable', '=', True),
        ])
        template_ids = templates.ids

        existing = subscription_model.search([
            ('user_id', '=', self.id),
            ('template_id', 'in', template_ids),
        ])
        existing_map = {rec.template_id.id: rec for rec in existing}

        to_create = []
        for template in templates:
            if template.id in existing_map:
                continue

            policy_name = template.subscription_policy_id.name
            policy = get_policy(policy_name)
            if not policy or not getattr(policy, 'subscribable', False):
                continue
            subscribed_by_default = bool(getattr(policy, 'subscribed_by_default', False))

            to_create.append({
                'user_id': self.id,
                'template_id': template.id,
                'is_subscribed': subscribed_by_default,
            })

        if to_create:
            subscription_model.create(to_create)

    @api.model_create_multi
    def create(self, vals_list):
        users = super().create(vals_list)
        for user in users.filtered(lambda user: not user.share):
            user._ensure_subscriptions_for_templates()
        return users
