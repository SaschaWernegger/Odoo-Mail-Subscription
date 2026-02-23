from odoo import fields, models


class MailSubscriptionPolicy(models.Model):
    """Policy registry for subscription behavior.

    Defines how subscriptions are stored and enforced per scope, enabling
    future extensions without hard-coded branching.
    """

    _name = 'mail.subscription.policy'
    _description = 'Email Subscription Policy'
    _rec_name = 'label'
    _order = 'sequence, id'
    _log_access = True

    sequence = fields.Integer(
        default=10,
        help='Order of policies in selection lists',
    )
    name = fields.Char(
        required=True,
        help='Technical name (used in code logic)',
    )
    label = fields.Char(
        required=True,
        help='User-friendly label shown in UI',
    )
    description = fields.Text(
        help='Detailed description of the policy behavior and implications',
    )

    def name_get(self):
        """Display label in selects instead of name."""
        return [(record.id, record.label) for record in self]
    
