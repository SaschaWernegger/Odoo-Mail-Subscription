from odoo.tests.common import TransactionCase, tagged

@tagged('standard', 'transactional_test')
class TestTransactionalPolicy(TransactionCase):

    def setUp(self):
        super().setUp()
        # setup your test data
        self.user1 = self.env['res.users'].create({
            'name': 'User 1',
            'login': 'user1@test.com',
            'email': 'user1@test.com',
        })
        self.partner1 = self.user1.partner_id
        
        val = self.env['mail.subscription.policy'].search([('name', '=', 'transactional')], limit=1).id
        self.template = self.env['mail.template'].create({
            'name': 'Transactional Template',
            'model_id': self.env['ir.model']._get('res.partner').id,
            'subscription_policy_id': val,
            'partner_to': '${object.id}',
            'auto_delete': False,
        })

    def test_transactional_always_sends(self):
        """Transactional emails should always be sent regardless of subscription."""
        mail_id = self.template.send_mail(
            self.partner1.id, force_send=True
        )

        mail_rec = self.env['mail.mail'].browse(mail_id)
        recipients = mail_rec.recipient_ids

        # both users should receive (direct recipients always get transactional)
        self.assertIn(self.partner1, recipients)

    def test_transactional_ignores_opt_out(self):
        """Transactional emails ignore opt-out subscriptions."""
        # Create opt-out subscription for user1
        self.env['user.mail.subscription'].create({
            'user_id': self.user1.id,
            'template_id': self.template.id,
        })

        # Send to partner1, which will also notify followers/etc.
        mail_id = self.template.send_mail(
            self.partner1.id, force_send=True
        )

        mail_rec = self.env['mail.mail'].browse(mail_id)
        recipients = mail_rec.recipient_ids

        # Direct recipient should always receive
        self.assertIn(self.partner1, recipients)

    def test_transactional_to_follower_ignores_opt_out(self):
        """Transactional emails to followers ignore opt-out (if follower subscription exists)."""
        # Make user1 follows himself
        self.env['mail.followers'].create({
            'res_model': 'res.partner',
            'res_id': self.partner1.id,
            'partner_id': self.partner1.id,
        })

        # Create opt-out subscription for user1
        self.env['user.mail.subscription'].create({
            'user_id': self.user1.id,
            'template_id': self.template.id,
        })

        mail_id = self.template.send_mail(
            self.partner1.id, force_send=True
        )

        mail_rec = self.env['mail.mail'].browse(mail_id)
        recipients = mail_rec.recipient_ids

        # Direct recipient should always receive
        self.assertIn(self.partner1, recipients)
