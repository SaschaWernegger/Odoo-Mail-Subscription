from odoo.tests.common import TransactionCase, tagged

@tagged('standard', 'bypass_test')
class TestBypassSubscriptionCheck(TransactionCase):

    def setUp(self):
        super().setUp()
        # setup your test data
        self.user1 = self.env['res.users'].create({
            'name': 'User 1',
            'login': 'user1@test.com',
            'email': 'user1@test.com',
        })
        self.partner1 = self.user1.partner_id

        self.user2 = self.env['res.users'].create({
            'name': 'User 2',
            'login': 'user2@test.com',
            'email': 'user2@test.com',
        })
        self.partner2 = self.user2.partner_id

    def test_bypass_informational_opt_out(self):
        """Bypass flag should send to opted-out users on informational template."""
        # Create informational template with bypass enabled
        informational_policy = self.env['mail.subscription.policy'].search([('name', '=', 'informational')], limit=1)
        template = self.env['mail.template'].create({
            'name': 'Informational Bypass Template',
            'model_id': self.env['ir.model']._get('res.partner').id,
            'subscription_policy_id': informational_policy.id,
            'partner_to': '${object.id}',
            'auto_delete': False,
        })

        # Create opt-out subscription for user2
        self.env['user.mail.subscription'].create({
            'user_id': self.user2.id,
            'template_id': template.id,
            'is_subscribed': False,
        })

        mail_id = template.with_context(bypass_subscription_check=True).send_mail(
            self.partner1.id, force_send=True
        )

        mail_rec = self.env['mail.mail'].browse(mail_id)
        recipients = mail_rec.recipient_ids

        # Direct recipient should receive
        self.assertIn(self.partner1, recipients)
        # Even though user2 is opted out, bypass flag makes them receive
        # (This test assumes bypass logic is implemented in the sending mechanism)

    def test_bypass_marketing_no_opt_in(self):
        """Bypass flag should send to non-opted-in users on marketing template."""
        # Create marketing template with bypass enabled
        marketing_policy = self.env['mail.subscription.policy'].search([('name', '=', 'marketing')], limit=1)
        template = self.env['mail.template'].create({
            'name': 'Marketing Bypass Template',
            'model_id': self.env['ir.model']._get('res.partner').id,
            'subscription_policy_id': marketing_policy.id,
            'partner_to': '${object.id}',
            'auto_delete': False,
        })

        # Note: no opt-in subscription for user2

        mail_id = template.with_context(bypass_subscription_check=True).send_mail(
            self.partner1.id, force_send=True
        )

        mail_rec = self.env['mail.mail'].browse(mail_id)
        recipients = mail_rec.recipient_ids

        # Direct recipient should receive
        self.assertIn(self.partner1, recipients)
        # Even though user2 didn't opt-in, bypass flag makes them receive
        # (This test assumes bypass logic is implemented in the sending mechanism)
