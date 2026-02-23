from .base import BasePolicy, register_policy


@register_policy
class TransactionalPolicy(BasePolicy):
    """Transactional emails; template always sent."""

    sequence = 40
    name = 'transactional'
    label = 'Transactional (Always Sent)'
    description = 'Users cannot control subscriptions. Template always sent (e.g., transactional emails).'

    def filter_recipients(self, mail, env) -> bool:
        return mail.partner_ids.ids