from odoo.tests.common import TransactionCase, tagged

@tagged('standard', 'opt_out_test')
class TestMailSubscription(TransactionCase):

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
        
        val = self.env['mail.subscription.policy'].search([('name', '=', 'informational')], limit=1).id
        self.template = self.env['mail.template'].create({
            'name': 'Test Template',
            'model_id': self.env['ir.model']._get('res.partner').id,
            'subscription_policy_id': val,
            'partner_to': '${object.id}',
            'auto_delete': False,
        })

    def test_send_mail_no_opt_out(self):
        # Simulate sending a mail
        mail_id = self.template.send_mail(
            self.partner1.id, force_send=True
        )

        # Check mail.mail recipients
        mail = self.env['mail.mail'].browse(mail_id).exists()
        recipients = mail.partner_ids

        # Only user1 should receive mail (user2 opted out)
        self.assertIn(self.partner1, recipients)

    def test_send_mail_filters_opt_out(self):
        # create a subscription for user2
        self.env['user.mail.subscription'].create({
            'user_id': self.user2.id,
            'template_id': self.template.id,
            'is_subscribed': False,
        })

        # Simulate sending a mail
        mail_id = self.template.send_mail(
            self.partner2.id, force_send=True
        )

        # Check mail.mail recipients
        mail = self.env['mail.mail'].browse(mail_id).exists()
        recipients = mail.partner_ids

        # Only user1 should receive mail (user2 opted out)
        self.assertNotIn(self.partner2, recipients)
        
    def test_opted_out_followers_still_receive_mail(self):

        # create a subscription for user2
        self.env['user.mail.subscription'].create({
            'user_id': self.user2.id,
            'template_id': self.template.id,
            'is_subscribed': False,
        })

        # Make user2 follow partner1
        self.env['mail.followers'].create({
            'res_model': 'res.partner',
            'res_id': self.partner1.id,
            'partner_id': self.partner2.id,
        })

        # Send mail to partner1 with both users as recipients
        mail_id = self.template.send_mail(
            self.partner1.id, 
            force_send=True,
            email_values={'partner_ids': [(6, 0, [self.partner1.id, self.partner2.id])]}
        )

        mail_rec = self.env['mail.mail'].browse(mail_id).exists()
        recipients = mail_rec.partner_ids

        # user2 IS a follower of partner1, so they SHOULD receive the mail
        # even though they opted out (followers bypass opt-out)
        self.assertIn(self.partner1, recipients)
        self.assertIn(self.partner2, recipients)
        
    def test_weekly_schedule(self):
        # Get or create the weekly frequency
        weekly_freq = self.env['mail.subscription.frequency'].search([('code', '=', 'weekly')], limit=1)
        if not weekly_freq:
            weekly_freq = self.env['mail.subscription.frequency'].create({'code': 'weekly'})
        
        # Create a subscription for user2 with weekly frequency
        self.env['user.mail.subscription'].create({
            'user_id': self.user2.id,
            'template_id': self.template.id,
            'is_subscribed': False,
            'subscribed_frequency_ids': [(6, 0, [weekly_freq.id])],
        })
        
        mail_id = self.template.with_context(mail_schedule_type='weekly').send_mail(
            self.partner2.id, force_send=True
        )

        mail_rec = self.env['mail.mail'].browse(mail_id).exists()
        recipients = mail_rec.partner_ids

        # assert expected recipients for weekly schedule
        self.assertIn(self.partner2, recipients)

    def test_direct_message_notifications_ignore_opt_out_filter(self):
        """Direct/chatter notifications should not be filtered by opt-out logic."""
        self.env['user.mail.subscription'].create({
            'user_id': self.user2.id,
            'template_id': self.template.id,
            'is_subscribed': False,
        })

        msg = self.env['mail.message'].create({
            'body': 'Direct notification test',
            'message_type': 'comment',
            'model': 'res.partner',
            'res_id': self.partner1.id,
        })

        mail = self.env['mail.mail'].create({
            'subject': 'Direct Notification',
            'body_html': '<p>Direct Notification</p>',
            'mail_message_id': msg.id,
            'recipient_ids': [(6, 0, [self.partner2.id])],
        })

        mail.with_context(
            mail_template_policy='informational',
            mail_template_id=self.template.id,
        )._filter_recipients_by_subscriptions()

        self.assertIn(self.partner2, mail.recipient_ids)
