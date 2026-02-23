from odoo import models, fields, api

from ..policies import get_policy


class UserMailSubscription(models.Model):
    _name = 'user.mail.subscription'
    _inherit = ['mail.thread']
    _description = 'User Email Subscription'

    _unique_user_template = models.Constraint(
        'unique(user_id, template_id)',
        'Each user/template must be unique',
    )

    user_id = fields.Many2one('res.users', required=True, ondelete='cascade', tracking=True)
    template_id = fields.Many2one('mail.template', required=True, ondelete='cascade', tracking=True)
    template_name = fields.Char(related='template_id.name', readonly=True)
    subscription_policy_id = fields.Many2one(related='template_id.subscription_policy_id', readonly=True, tracking=True)
    subscription_policy_label = fields.Char(related='subscription_policy_id.label', readonly=True, string='Policy')
    template_group_label = fields.Char(
        string='Group',
        compute='_compute_template_group_label',
        store=True,
        readonly=True,
        tracking=True
    )
    user_role_label = fields.Char(
        string='Role',
        compute='_compute_user_role_label',
        store=True,
        readonly=True,
    )

    subscribed_frequency_ids = fields.Many2many(
        'mail.subscription.frequency',
        'user_mail_subscription_subscribed_frequency_rel',
        'subscription_id',
        'frequency_id',
        string='Subscribed Frequencies',
        tracking=True,
    )
    is_subscribed = fields.Boolean(
        string='Subscribed',
        default=True,
        tracking=True,
        help='Stored subscription status for this user/template pair.',
        inverse='_inverse_is_subscribed',
    )

    frequency_immediate = fields.Boolean(
        string='Immediate',
        compute='_compute_frequency_toggles',
        inverse='_inverse_frequency_immediate',
        readonly=False,
    )
    frequency_daily = fields.Boolean(
        string='Daily',
        compute='_compute_frequency_toggles',
        inverse='_inverse_frequency_daily',
        readonly=False,
    )
    frequency_weekly = fields.Boolean(
        string='Weekly',
        compute='_compute_frequency_toggles',
        inverse='_inverse_frequency_weekly',
        readonly=False,
    )
    frequency_monthly = fields.Boolean(
        string='Monthly',
        compute='_compute_frequency_toggles',
        inverse='_inverse_frequency_monthly',
        readonly=False,
    )

    @api.depends('template_id', 'template_id.template_group')
    def _compute_template_group_label(self):
        selection = self.env['mail.template']._fields['template_group'].selection
        if callable(selection):
            selection = selection(self.env['mail.template'])
        group_labels = dict(selection or [])
        for record in self:
            record.template_group_label = group_labels.get(record.template_id.template_group, '')

    @api.depends('user_id', 'user_id.share', 'user_id.group_ids')
    def _compute_user_role_label(self):
        admin_group = self.env.ref('base.group_system', raise_if_not_found=False)
        admin_group_id = admin_group.id if admin_group else False
        for record in self:
            user = record.user_id
            if not user:
                record.user_role_label = ''
            elif user.share:
                record.user_role_label = 'External User'
            elif admin_group_id and admin_group_id in user.group_ids.ids:
                record.user_role_label = 'Administrator'
            else:
                record.user_role_label = 'Internal User'

    @api.depends('subscribed_frequency_ids')
    def _compute_frequency_toggles(self):
        frequency_codes = {freq.code for freq in self.env['mail.subscription.frequency'].search([])}
        for record in self:
            enabled_codes = set(record.subscribed_frequency_ids.mapped('code'))
            record.frequency_immediate = 'immediate' in enabled_codes
            record.frequency_daily = 'daily' in enabled_codes
            record.frequency_weekly = 'weekly' in enabled_codes
            record.frequency_monthly = 'monthly' in enabled_codes

    def _set_frequency_enabled(self, frequency_code, enabled):
        """Helper to add/remove frequency from subscribed_frequency_ids."""
        frequency_model = self.env['mail.subscription.frequency'].sudo()
        frequency = frequency_model.search([('code', '=', frequency_code)], limit=1)
        if not frequency:
            frequency = frequency_model.create({'code': frequency_code})
        
        for record in self:
            if enabled:
                record.subscribed_frequency_ids = [(4, frequency.id)]
            else:
                record.subscribed_frequency_ids = [(3, frequency.id)]
            record._sync_is_subscribed_from_frequencies()

    def _sync_is_subscribed_from_frequencies(self):
        """Keep is_subscribed aligned with frequency toggles."""
        if self.env.context.get('skip_is_subscribed_inverse'):
            return
        for record in self:
            enabled = bool(record.subscribed_frequency_ids)
            record.with_context(skip_is_subscribed_inverse=True).write({
                'is_subscribed': enabled,
            })

    @api.model_create_multi
    def create(self, vals_list):
        records = super(UserMailSubscription, self.with_context(
            skip_is_subscribed_inverse=True
        )).create(vals_list)
        for record, vals in zip(records, vals_list):
            if 'subscribed_frequency_ids' in vals:
                record._sync_is_subscribed_from_frequencies()
        return records

    def write(self, vals):
        res = super().write(vals)
        if 'subscribed_frequency_ids' in vals:
            self._sync_is_subscribed_from_frequencies()
        return res

    def _inverse_frequency_immediate(self):
        for record in self:
            record._set_frequency_enabled('immediate', record.frequency_immediate)

    def _inverse_frequency_daily(self):
        for record in self:
            record._set_frequency_enabled('daily', record.frequency_daily)

    def _inverse_frequency_weekly(self):
        for record in self:
            record._set_frequency_enabled('weekly', record.frequency_weekly)

    def _inverse_frequency_monthly(self):
        for record in self:
            record._set_frequency_enabled('monthly', record.frequency_monthly)

    def _inverse_is_subscribed(self):
        """When toggling subscription, enable/disable all frequencies accordingly."""
        if self.env.context.get('skip_is_subscribed_inverse'):
            return
        for record in self:
            if record.is_subscribed:
                # Enable all frequencies
                record._set_frequency_enabled('immediate', True)
                record._set_frequency_enabled('daily', True)
                record._set_frequency_enabled('weekly', True)
                record._set_frequency_enabled('monthly', True)
            else:
                # Disable all frequencies
                record._set_frequency_enabled('immediate', False)
                record._set_frequency_enabled('daily', False)
                record._set_frequency_enabled('weekly', False)
                record._set_frequency_enabled('monthly', False)

    def action_bulk_subscribe(self):
        """Bulk action to mark selected subscriptions as subscribed."""
        if self:
            self.write({'is_subscribed': True})
        return {'type': 'ir.actions.client', 'tag': 'reload'}

    def action_bulk_unsubscribe(self):
        """Bulk action to mark selected subscriptions as unsubscribed."""
        if self:
            self.write({'is_subscribed': False})
        return {'type': 'ir.actions.client', 'tag': 'reload'}

    def action_bulk_reset_to_default(self):
        """Bulk action to reset selected subscriptions to policy defaults."""
        for subscription in self:
            policy_name = subscription.subscription_policy_id.name if subscription.subscription_policy_id else None
            policy = get_policy(policy_name) if policy_name else None
            subscribed_by_default = bool(getattr(policy, 'subscribed_by_default', False))
            subscription.write({
                'is_subscribed': subscribed_by_default,
                'subscribed_frequency_ids': [(5, 0, 0)],
            })
        return {'type': 'ir.actions.client', 'tag': 'reload'}

    def unlink(self):
        """Ensure Many2many relation rows are removed when subscriptions are deleted.

        This keeps the relation tables clean when records are removed (for example
        when a template's subscriptions are reset and the subscription records
        get unlinked by the template logic).
        """
        if not self:
            return super(UserMailSubscription, self).unlink()
        ids = self.ids
        # Remove subscribed frequency links
        self.env.cr.execute(
            "DELETE FROM user_mail_subscription_subscribed_frequency_rel WHERE subscription_id = ANY(%s)",
            (ids,)
        )
        return super(UserMailSubscription, self).unlink()
