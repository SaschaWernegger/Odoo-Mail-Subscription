import logging

from odoo import models, fields, api
from ..policies import get_registered_policies, get_policy

_logger = logging.getLogger(__name__)

class MailTemplate(models.Model):
    _inherit = 'mail.template'
    
    _track = {
        'subscription_policy_id': {
            'name': 'Subscription Policy',
        },
        'template_group': {
            'name': 'Template Group',
        },
    }

    user_mail_subscription_ids = fields.One2many(
        'user.mail.subscription',
        'template_id',
        string="Mail Subscriptions"
    )

    is_user_subscribable = fields.Boolean(
        string="User Subscription Possible",
        compute='_compute_is_user_subscribable',
        store=True,
        readonly=True,
        help="Computed from subscription policy registry.",
    )
    
    
    subscription_policy_id = fields.Many2one(
        'mail.subscription.policy',
        string='Subscription Policy',
        help='Controls subscription behavior and UI for this template',
    )

    applicable_policy_ids = fields.Many2many(
        'mail.subscription.policy',
        compute='_compute_applicable_policies',
        string='Applicable Subscription Policies',
        help='Policies that apply to this template (used to limit selectable options in the UI)'
    )
    
    template_group = fields.Selection(
        selection=[
            ('sales', 'Sales Reports'),
            ('inventory', 'Inventory Alerts'),
            ('hr', 'HR Notifications'),
        ],
        string="Template Group",
        help="Grouping category for organizing templates in user notification tab",
    )
    
    subscription_count = fields.Integer(
        string="Subscriptions Count",
        compute='_compute_subscription_count',
        help="Number of subscription entries for this template"
    )
    policy_is_subscribable = fields.Boolean(
        string='Policy Is Subscribable',
        compute='_compute_policy_is_subscribable',
        help='Technical helper to control UI visibility for subscribable policies.',
    )

    current_user_subscribed = fields.Boolean(
        compute='_compute_current_user_subscribed',
        inverse='_inverse_current_user_subscribed',
        compute_sudo=True,
        readonly=False,
        string="Subscribed",
        help="Whether the current user is subscribed to this template"
    )

    frequency_immediate_enabled = fields.Boolean(
        string='Immediate',
        compute='_compute_frequency_toggles',
        inverse='_inverse_frequency_immediate_enabled',
        readonly=False,
        compute_sudo=True,
    )
    frequency_daily_enabled = fields.Boolean(
        string='Daily',
        compute='_compute_frequency_toggles',
        inverse='_inverse_frequency_daily_enabled',
        readonly=False,
        compute_sudo=True,
    )
    frequency_weekly_enabled = fields.Boolean(
        string='Weekly',
        compute='_compute_frequency_toggles',
        inverse='_inverse_frequency_weekly_enabled',
        readonly=False,
        compute_sudo=True,
    )
    frequency_monthly_enabled = fields.Boolean(
        string='Monthly',
        compute='_compute_frequency_toggles',
        inverse='_inverse_frequency_monthly_enabled',
        readonly=False,
        compute_sudo=True,
    )
    def send_mail(
        self,
        res_id,
        force_send=False,
        raise_exception=False,
        email_values=None,
        email_layout_xmlid=None,
    ):
        email_values = dict(email_values or {})
        headers = dict(email_values.get("headers", {}))

        subscription_policy = self.subscription_policy_id.name if self.subscription_policy_id else "None"
        headers.update({
            "X-My-Template-ID": str(self.id),
            "X-My-Subscription-Policy": subscription_policy,
        })

        email_values["headers"] = headers

        template = self.with_context(
            mail_template_id=self.id,
            mail_template_policy=subscription_policy,
        )

        return super(MailTemplate, template).send_mail(
            res_id,
            force_send=force_send,
            raise_exception=raise_exception,
            email_values=email_values,
            email_layout_xmlid=email_layout_xmlid,
        )

    # ========== Computed Fields & Triggers ==========
    
    @api.depends('user_mail_subscription_ids', 'user_mail_subscription_ids.is_subscribed')
    def _compute_subscription_count(self):
        """Compute the count of active (subscribed) entries for this template."""
        for template in self:
            template.subscription_count = len(
                template.user_mail_subscription_ids.filtered(lambda sub: sub.is_subscribed)
            )

    @api.depends('subscription_policy_id')
    def _compute_is_user_subscribable(self):
        """Compute whether users can subscribe based on the policy registry."""
        for template in self:
            policy = template._get_policy_definition()
            template.is_user_subscribable = bool(getattr(policy, 'subscribable', False))

    @api.depends('subscription_policy_id')
    def _compute_policy_is_subscribable(self):
        """Compute whether selected policy is subscribable using policy registry."""
        for template in self:
            template.policy_is_subscribable = bool(template.is_user_subscribable)

    @api.depends('user_mail_subscription_ids', 'subscription_policy_id')
    def _compute_current_user_subscribed(self):
        """Compute current user's subscription state for this template."""
        subscription_user = self._get_subscription_user()
        for template in self:
            if not template._is_user_subscribable():
                # Transactional/unsupported policies are always treated as subscribed
                template.current_user_subscribed = True
                continue

            subscription = template._get_user_subscription(subscription_user)
            if subscription:
                template.current_user_subscribed = bool(subscription.is_subscribed)
                continue

            policy = template._get_policy_definition()
            template.current_user_subscribed = bool(getattr(policy, 'subscribed_by_default', False))

    def _inverse_current_user_subscribed(self):
        """Persist current user's toggle state based on policy mode."""
        subscription_user = self._get_subscription_user()
        for template in self:
            if not template._is_user_subscribable():
                continue

            subscription = template._get_user_subscription(subscription_user)
            if not subscription:
                subscription = self.env['user.mail.subscription'].create({
                    'user_id': subscription_user.id,
                    'template_id': template.id,
                    'is_subscribed': template.current_user_subscribed,
                })
            else:
                subscription.write({'is_subscribed': template.current_user_subscribed})

    @api.depends('user_mail_subscription_ids', 'subscription_policy_id')
    def _compute_frequency_toggles(self):
        subscription_user = self._get_subscription_user()
        for template in self:
            template.frequency_immediate_enabled = False
            template.frequency_daily_enabled = False
            template.frequency_weekly_enabled = False
            template.frequency_monthly_enabled = False

            if not template._is_informational_policy() or not template._is_user_subscribable():
                continue

            subscription = template._get_user_subscription(subscription_user)
            if not subscription:
                continue

            enabled_codes = set(subscription.subscribed_frequency_ids.mapped('code'))
            template.frequency_immediate_enabled = 'immediate' in enabled_codes
            template.frequency_daily_enabled = 'daily' in enabled_codes
            template.frequency_weekly_enabled = 'weekly' in enabled_codes
            template.frequency_monthly_enabled = 'monthly' in enabled_codes

    def _set_frequency_enabled(self, frequency_code, enabled):
        frequency_model = self.env['mail.subscription.frequency'].sudo()
        frequency = frequency_model.search([('code', '=', frequency_code)], limit=1)
        if not frequency:
            frequency = frequency_model.create({'code': frequency_code})

        subscription_user = self._get_subscription_user()

        for template in self:
            if not template._is_informational_policy() or not template._is_user_subscribable():
                continue

            subscription = template._get_user_subscription(subscription_user)
            if not subscription and enabled:
                subscription = self.env['user.mail.subscription'].create({
                    'user_id': subscription_user.id,
                    'template_id': template.id,
                    'is_subscribed': True,
                })

            if not subscription:
                continue

            if enabled:
                subscription.write({'subscribed_frequency_ids': [(4, frequency.id)]})
            else:
                subscription.write({'subscribed_frequency_ids': [(3, frequency.id)]})

    def _inverse_frequency_immediate_enabled(self):
        for template in self:
            template._set_frequency_enabled('immediate', template.frequency_immediate_enabled)

    def _inverse_frequency_daily_enabled(self):
        for template in self:
            template._set_frequency_enabled('daily', template.frequency_daily_enabled)

    def _inverse_frequency_weekly_enabled(self):
        for template in self:
            template._set_frequency_enabled('weekly', template.frequency_weekly_enabled)

    def _inverse_frequency_monthly_enabled(self):
        for template in self:
            template._set_frequency_enabled('monthly', template.frequency_monthly_enabled)

    def _get_subscription_user(self):
        """Return the user targeted by subscription fields.

        Uses context key `subscription_user_id` when provided (e.g., from
        `res.users` form view), otherwise falls back to the current user.
        """
        user_id = self.env.context.get('subscription_user_id')
        if user_id:
            user = self.env['res.users'].browse(user_id)
            if user.exists():
                return user
        return self.env.user

    def _get_policy_definition(self):
        """Return registered policy object for this template, if available."""
        self.ensure_one()
        policy = self.subscription_policy_id.name if self.subscription_policy_id else None
        return get_policy(policy) if policy else None

    def _is_subscribable_policy(self):
        """Return whether template policy is subscribable by users."""
        self.ensure_one()
        policy = self._get_policy_definition()
        return bool(getattr(policy, 'subscribable', False))

    def _is_user_subscribable(self):
        """Return whether users can subscribe to this template."""
        self.ensure_one()
        return bool(self.is_user_subscribable)

    def _is_informational_policy(self):
        """Return whether template policy supports frequency toggles."""
        self.ensure_one()
        return bool(self.subscription_policy_id and self.subscription_policy_id.name == 'informational')

    def _get_user_subscription(self, user):
        """Return subscription record for user and template, if any."""
        self.ensure_one()
        return self.env['user.mail.subscription'].search([
            ('user_id', '=', user.id),
            ('template_id', '=', self.id),
        ], limit=1)
    
    def _compute_applicable_policies(self):
        """Compute which subscription policies apply to each template.

        Uses the in-memory policy registry (defined in `my_mail.policies`) and matches
        registered policy instances to persisted `mail.subscription.policy` records
        by the policy `name` field.
        """
        policy_model = self.env['mail.subscription.policy']
        registered = get_registered_policies() or []

        for template in self:
            applicable_ids = []
            for policy in registered:
                try:
                    if policy.valid_on(template):
                        policy_name = getattr(policy, 'name', None)
                        if not policy_name:
                            continue
                        rec = policy_model.search([('name', '=', policy_name)], limit=1)
                        if rec:
                            applicable_ids.append(rec.id)
                except Exception:
                    _logger.exception(
                        "Error evaluating policy '%s' for template '%s'",
                        getattr(policy, 'name', '<unknown>'), template.name,
                    )

            template.applicable_policy_ids = [(6, 0, applicable_ids)]

    # ========== UI Actions ==========
    
    def action_open_template_subscriptions(self):
        """Open subscription list for the current template."""
        self.ensure_one()

        list_view = self.env.ref('my_mail.view_user_mail_subscription_list_template').id
        form_view = self.env.ref('my_mail.view_user_mail_subscription_form_user').id

        return {
            'name': f"Subscriptions: {self.name}",
            'type': 'ir.actions.act_window',
            'res_model': 'user.mail.subscription',
            'view_mode': 'list,form',
            'views': [(list_view, 'list'), (form_view, 'form')],
            'target': 'current',
            'domain': [('template_id', '=', self.id)],
            'context': {
                'default_template_id': self.id,
                'group_by': 'user_role_label',
                'from_template_view': True,
            }
        }

    def action_reset_subscriptions(self):
        """Reset all subscriptions to policy defaults without deleting rows."""
        self.ensure_one()

        policy_name = self.subscription_policy_id.name if self.subscription_policy_id else None
        policy = get_policy(policy_name) if policy_name else None
        subscribed_by_default = bool(getattr(policy, 'subscribed_by_default', False))

        self.user_mail_subscription_ids.write({
            'is_subscribed': subscribed_by_default,
            'subscribed_frequency_ids': [(5, 0, 0)],
        })
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'mail.template',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def write(self, vals):
        """Override write to synchronize subscriptions on policy transitions.

        Transition rules on policy change:
        - subscribable -> non-subscribable: delete all template subscriptions
        - non-subscribable -> subscribable: create subscriptions for all internal users
        - subscribable -> subscribable (different policy): keep rows, reset defaults
        """
        old_policy_names = {
            template.id: (template.subscription_policy_id.name if template.subscription_policy_id else None)
            for template in self
        }

        res = super().write(vals)

        if 'subscription_policy_id' not in vals:
            return res

        user_model = self.env['res.users'].sudo()
        subscription_model = self.env['user.mail.subscription'].sudo()
        internal_users = user_model.search([('share', '=', False)])

        for template in self:
            old_policy_name = old_policy_names.get(template.id)
            new_policy_name = template.subscription_policy_id.name if template.subscription_policy_id else None

            if old_policy_name == new_policy_name:
                continue

            old_policy = get_policy(old_policy_name) if old_policy_name else None
            new_policy = get_policy(new_policy_name) if new_policy_name else None

            old_subscribable = bool(
                (old_policy and getattr(old_policy, 'subscribable', False))
            )
            new_subscribable = bool(
                (new_policy and getattr(new_policy, 'subscribable', False))
            )

            # Subscribable -> non-subscribable: remove all rows
            if old_subscribable and not new_subscribable:
                template_subscriptions = subscription_model.search([('template_id', '=', template.id)])
                subs_count = len(template_subscriptions)
                template_subscriptions.unlink()
                _logger.info(
                    "Deleted %d subscriptions for template '%s' due to policy becoming non-subscribable",
                    subs_count,
                    template.name,
                )
                continue

            if not new_subscribable:
                continue

            default_subscribed = bool(getattr(new_policy, 'subscribed_by_default', False))

            existing = subscription_model.search([
                ('template_id', '=', template.id),
                ('user_id', 'in', internal_users.ids),
            ])
            existing_user_ids = set(existing.mapped('user_id').ids)

            # non-subscribable -> subscribable: create rows for all users
            # subscribable -> subscribable (different policy): ensure missing rows exist too
            to_create = []
            for user in internal_users:
                if user.id in existing_user_ids:
                    continue
                to_create.append({
                    'user_id': user.id,
                    'template_id': template.id,
                    'is_subscribed': default_subscribed,
                })
            if to_create:
                subscription_model.create(to_create)

            # subscribable -> subscribable with different policy: reset all defaults
            if old_subscribable and new_subscribable:
                subs_to_reset = subscription_model.search([('template_id', '=', template.id)])
                subs_to_reset.write({
                    'is_subscribed': default_subscribed,
                    'subscribed_frequency_ids': [(5, 0, 0)],
                })

        return res

    @api.model_create_multi
    def create(self, vals_list):
        """Ensure subscribable templates default to user-subscribable when policy allows it."""
        return super().create(vals_list)
