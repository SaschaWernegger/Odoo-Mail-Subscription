from odoo.tests.common import TransactionCase, tagged

@tagged('standard', 'opt_in_test')
class TestMarketingPolicy(TransactionCase):

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
        
        val = self.env['mail.subscription.policy'].search([('name', '=', 'marketing')], limit=1).id
        self.template = self.env['mail.template'].create({
            'name': 'Marketing Template',
            'model_id': self.env['ir.model']._get('res.partner').id,
            'subscription_policy_id': val,
            'partner_to': '${object.id}',
            'auto_delete': False,
        })

    def test_no_opt_in_user_does_not_receive_mail(self):
        """User not opted in should not receive marketing mail."""
        mail_id = self.template.send_mail(
            self.partner1.id, force_send=True
        )

        # Check mail.mail recipients
        mail = self.env['mail.mail'].browse(mail_id).exists()
        recipients = mail.partner_ids

        # user2 not opted in, should not receive
        self.assertNotIn(self.partner1, recipients)

    def test_opted_in_user_receives_mail(self):
        """User opted in should receive marketing mail."""
        # Create opt-in subscription for user2
        self.env['user.mail.subscription'].create({
            'user_id': self.user2.id,
            'template_id': self.template.id,
            'is_subscribed': True,
        })

        mail_id = self.template.send_mail(
            self.partner2.id, force_send=True
        )

        mail_rec = self.env['mail.mail'].browse(mail_id)
        recipients = mail_rec.recipient_ids

        # user2 opted in, should receive
        self.assertIn(self.partner2, recipients)

    def test_not_opted_in_but_following_receives_mail(self):
        """User not opted in but following should receive marketing mail."""
        # Make user2 follow partner1
        self.env['mail.followers'].create({
            'res_model': 'res.partner',
            'res_id': self.partner1.id,
            'partner_id': self.partner2.id,
        })

        mail_id = self.template.send_mail(
            self.partner2.id, force_send=True
        )

        mail_rec = self.env['mail.mail'].browse(mail_id)
        recipients = mail_rec.recipient_ids

        # user2 not opted in but is following, should receive
        self.assertIn(self.partner2, recipients)
