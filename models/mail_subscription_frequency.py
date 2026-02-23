from odoo import api, fields, models


class MailSubscriptionFrequency(models.Model):
    _name = 'mail.subscription.frequency'
    _description = 'Mail Subscription Frequency'

    _unique_code = models.Constraint(
        'unique(code)',
        'Frequency code must be unique',
    )

    code = fields.Selection(
        [
            ('immediate', 'Immediate'),
            ('daily', 'Daily'),
            ('weekly', 'Weekly'),
            ('monthly', 'Monthly'),
        ],
        required=True,
        string='Code',
    )
    name = fields.Char(string='Name', compute='_compute_name', store=True)

    @api.depends('code')
    def _compute_name(self):
        for record in self:
            record.name = dict(self._fields['code'].selection).get(record.code, record.code)
