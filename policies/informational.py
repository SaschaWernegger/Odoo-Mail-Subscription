from .base import BasePolicy, register_policy

@register_policy
class InformationalPolicy(BasePolicy):
    """
        A Policy where users are subscribed by default and can opt-out and looking for scheduling.
        If this policy should be used on other scheduled actions they should also pass the frequency 
        in the context to the mail template as "mail_schedule_type", "immediate" is also supported to 
        be passed in this field or True in mail_notify_force_send.
        
        Supported frequencies:
            * immediate
            * daily
            * weekly
            * monthly
"""

    sequence = 10
    name = 'informational'
    label = 'Informational (Default Subscribed)'
    description = 'Users are subscribed by default and can opt-out of receiving this template. Follower still receives emails even if opted out.'
    subscribed_by_default = True
    subscribable = True

    def should_filter(self, mail, env) -> bool:
        message = mail.mail_message_id
        if not message:
            return True
        return message.message_type not in ('comment', 'notification')

    def filter_recipients(self, mail, env):
        """ filter_recipients for informational policy:
            - Get all followers of the message's record and their corresponding users (these are always subscribed)
            - For non-followers, check if they have an opt-out subscription for this template
            - If there's a frequency context (e.g., from a scheduled action), also check if the user has that frequency enabled in their subscription and exclude them if so
            - Return the original recipients minus any opted-out users (followers are never excluded)
        """
        
        message = mail.mail_message_id
        template_id = env.context.get('mail_template_id')
        if not template_id:
            return mail.partner_ids

        # Filter followers first (they bypass opt-out)
        following_recipients = mail.env['mail.followers'].search([
            ('res_model', '=', message.model),
            ('res_id', '=', message.res_id),
            ('partner_id', 'in', mail.partner_ids.ids)
        ]).mapped('partner_id.user_ids')
        not_following_recipients = mail.partner_ids.user_ids - following_recipients

        # Check opt-out subscriptions for non-followers
        opted_out_subscriptions = mail.env['user.mail.subscription'].search([
            ('user_id', 'in', not_following_recipients.ids),
            ('template_id', '=', template_id),
            ('is_subscribed', '=', False),
        ])

        # If there's a frequency context, exclude users who have that frequency enabled
        immediate = env.context.get('mail_notify_force_send', False)
        frequency_code = "immediate" if immediate else env.context.get('mail_schedule_type')
        
        if frequency_code:
            opted_out_subscriptions = opted_out_subscriptions.filtered(
                lambda s: frequency_code not in s.subscribed_frequency_ids.mapped('code')
            )
        opted_out_recipients = opted_out_subscriptions.mapped('user_id.partner_id')

        return mail.partner_ids - opted_out_recipients