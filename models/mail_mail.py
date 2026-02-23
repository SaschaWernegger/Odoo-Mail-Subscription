from odoo import models, api

from ..policies import get_policy


class MailMail(models.Model):
    _inherit = 'mail.mail'

    def _get_subscription_template(self):
        """Return template record used for subscription filtering, if available.

        Odoo 19 mail.mail does not expose a direct template field by default.
        This helper keeps compatibility by checking known field names.
        """
        self.ensure_one()
        if 'template_id' in self._fields and self.template_id:
            return self.template_id
        if 'mail_template_id' in self._fields and self.mail_template_id:
            return self.mail_template_id
        return self.env['mail.template']
    
    def _send(self, auto_commit=False, raise_exception=False,
              smtp_session=None, **kwargs):
        """Override mail sending to respect subscription policies.

        Uses the policy registry to filter ``partner_ids`` before sending.
        The ``email_to`` field is never modified.
        """
        bypass_filter = self.env.context.get('bypass_subscription_check', False)

        if not bypass_filter:
            for mail in self:
                mail._filter_recipients_by_subscriptions()
                
        return super()._send(
            auto_commit=auto_commit,
            raise_exception=raise_exception,
            smtp_session=smtp_session,
            **kwargs
        )
    
    def _filter_recipients_by_subscriptions(self):
        """Filter mail recipients using the policy registry.

        The policy ``filter_recipients`` method must return the partner
        recordset or list of partner IDs that should receive the mail.
        """
        self.ensure_one()

        if self.env.context.get('bypass_subscription_check'):
            return self.partner_ids.ids

        all_partner_ids = self.partner_ids.ids
        policy_name = self.env.context.get('mail_template_policy')
        policy = get_policy(policy_name)
        if not policy:
            return all_partner_ids

        if not policy.should_filter(self, self.env):
            return all_partner_ids

        filtered = policy.filter_recipients(self, self.env)
        if filtered is True or filtered is False or filtered is None:
            return all_partner_ids

        if isinstance(filtered, models.BaseModel):
            partner_ids = filtered.ids
        else:
            partner_ids = list(filtered)

        if set(partner_ids) != set(self.partner_ids.ids):
            self.partner_ids = [(6, 0, partner_ids)]

        return partner_ids
    
    @api.model
    def create(self, vals):
        """Override create to handle subscription filtering on mail creation.
        
        This ensures subscription logic is applied when mail.mail records
        are created programmatically.
        """
        record = super().create(vals)
        
        # Check if we should apply subscription filter
        bypass_filter = self.env.context.get('bypass_subscription_check', False)
        
        template = record._get_subscription_template()
        if not bypass_filter and template:
            record._filter_recipients_by_subscriptions()
        
        return record
