from .base import BasePolicy, register_policy
from .informational import InformationalPolicy


@register_policy
class MarketingPolicy(InformationalPolicy):
    """Users unsubscribed by default; must opt-in manually."""

    sequence = 20
    name = 'marketing'
    label = 'Marketing (Default Unsubscribed)'
    description = 'Users are unsubscribed by default and must explicitly opt-in to receive this template.'
    subscribed_by_default = False
    subscribable = True

    def filter_recipients(self, mail, env):
        """Filter recipients for marketing policy (opt-in).

        - Followers always receive the mail.
        - Non-followers must have an explicit subscription with
          ``is_subscribed=True``.
        - If a schedule/frequency context is present, keep only subscriptions
          matching that frequency when frequencies are configured.
        """
        template_id = env.context.get('mail_template_id')
        if not template_id:
            return mail.partner_ids

        message = mail.mail_message_id
        following_users = mail.env['res.users']
        if message:
            following_users = mail.env['mail.followers'].search([
                ('res_model', '=', message.model),
                ('res_id', '=', message.res_id),
                ('partner_id', 'in', mail.partner_ids.ids),
            ]).mapped('partner_id.user_ids')

        non_following_users = mail.partner_ids.user_ids - following_users

        opted_in_subscriptions = mail.env['user.mail.subscription'].search([
            ('user_id', 'in', non_following_users.ids),
            ('template_id', '=', template_id),
            ('is_subscribed', '=', True),
        ])

        immediate = env.context.get('mail_notify_force_send', False)
        frequency_code = 'immediate' if immediate else env.context.get('mail_schedule_type')
        if frequency_code:
            opted_in_subscriptions = opted_in_subscriptions.filtered(
                lambda s: not s.subscribed_frequency_ids
                or frequency_code in s.subscribed_frequency_ids.mapped('code')
            )

        allowed_partners = following_users.partner_id | opted_in_subscriptions.mapped('user_id.partner_id')
        return mail.partner_ids & allowed_partners
