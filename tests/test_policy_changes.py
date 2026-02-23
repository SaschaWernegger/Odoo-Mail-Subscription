from odoo.tests import TransactionCase, tagged


@tagged('standard', 'policy_change')
class TestMailTemplatePolicyChanges(TransactionCase):
    """Test subscription policy change transitions."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.model_res_partner = cls.env.ref('base.model_res_partner')
        cls.policy_model = cls.env['mail.subscription.policy']

        cls.informational_policy = cls.policy_model.search([('name', '=', 'informational')], limit=1)
        cls.marketing_policy = cls.policy_model.search([('name', '=', 'marketing')], limit=1)
        cls.transactional_policy = cls.policy_model.search([('name', '=', 'transactional')], limit=1)

        # Create a test template starting as informational
        cls.template = cls.env['mail.template'].create({
            'name': 'Test Template for Type Changes',
            'model_id': cls.model_res_partner.id,
            'subject': 'Test Subject',
            'body_html': '<p>Test Body</p>',
            'subscription_policy_id': cls.informational_policy.id,
        })

    def test_change_from_subscribable_to_subscribable_resets_defaults(self):
        """Changing informational -> marketing keeps rows and resets defaults."""
        user = self.env['res.users'].create({
            'name': 'Test User',
            'login': 'testuser@test.com',
            'email': 'testuser@test.com',
        })

        subscription = self.env['user.mail.subscription'].search([
            ('user_id', '=', user.id),
            ('template_id', '=', self.template.id),
        ], limit=1)
        self.assertTrue(subscription)

        # move away from defaults first
        subscription.write({'is_subscribed': True})
        self.assertTrue(subscription.is_subscribed)

        self.template.subscription_policy_id = self.marketing_policy

        subscription = self.env['user.mail.subscription'].browse(subscription.id)
        self.assertTrue(subscription.exists())
        self.assertFalse(subscription.is_subscribed)

    def test_change_from_subscribable_to_non_subscribable_deletes_rows(self):
        """Changing marketing -> transactional deletes template subscription rows."""
        marketing_template = self.env['mail.template'].create({
            'name': 'Marketing Template',
            'model_id': self.model_res_partner.id,
            'subscription_policy_id': self.marketing_policy.id,
            'subject': 'Marketing Subject',
            'body_html': '<p>Marketing Body</p>',
        })

        user = self.env['res.users'].create({
            'name': 'Test User 2',
            'login': 'testuser2@test.com',
            'email': 'testuser2@test.com',
        })

        subscription = self.env['user.mail.subscription'].search([
            ('user_id', '=', user.id),
            ('template_id', '=', marketing_template.id),
        ], limit=1)
        self.assertTrue(subscription.exists())

        marketing_template.subscription_policy_id = self.transactional_policy

        self.assertFalse(subscription.exists())

    def test_change_from_non_subscribable_to_subscribable_creates_rows(self):
        """Changing transactional -> informational creates rows for internal users."""
        transactional_template = self.env['mail.template'].create({
            'name': 'Transactional to Informational Template',
            'model_id': self.model_res_partner.id,
            'subscription_policy_id': self.transactional_policy.id,
            'subject': 'Transactional Subject',
            'body_html': '<p>Transactional Body</p>',
        })

        user = self.env['res.users'].create({
            'name': 'Transition User',
            'login': 'transition_user@test.com',
            'email': 'transition_user@test.com',
        })

        subscription = self.env['user.mail.subscription'].search([
            ('user_id', '=', user.id),
            ('template_id', '=', transactional_template.id),
        ], limit=1)
        self.assertFalse(subscription)

        transactional_template.subscription_policy_id = self.informational_policy

        subscription = self.env['user.mail.subscription'].search([
            ('user_id', '=', user.id),
            ('template_id', '=', transactional_template.id),
        ], limit=1)
        self.assertTrue(subscription)
        self.assertTrue(subscription.is_subscribed)

    def test_new_users_should_receive_transactional_emails(self):
        """New users should receive transactional emails."""
        transactional_template = self.env['mail.template'].create({
            'name': 'Transactional Template',
            'model_id': self.model_res_partner.id,
            'subscription_policy_id': self.transactional_policy.id,
            'subject': 'Transactional Subject',
            'body_html': '<p>Transactional Body</p>',
            'partner_to': '${object.id}',
            'auto_delete': False,
        })
        
        # Create new user
        new_user = self.env['res.users'].create({
            'name': 'New User',
            'login': 'newuser@test.com',
            'email': 'newuser@test.com',
        })
        new_partner = new_user.partner_id
        
        # Send transactional mail to new user's partner
        mail_id = transactional_template.send_mail(new_partner.id, force_send=True)
        
        # Verify mail was sent to the new user
        mail_rec = self.env['mail.mail'].browse(mail_id)
        recipients = mail_rec.recipient_ids

        self.assertIn(new_partner, recipients)

    def test_new_users_should_not_receive_marketing_emails(self):
        """New users should not receive marketing emails unless they opt-in."""
        marketing_template = self.env['mail.template'].create({
            'name': 'Marketing Template',
            'model_id': self.model_res_partner.id,
            'subscription_policy_id': self.marketing_policy.id,
            'subject': 'Marketing Subject',
            'body_html': '<p>Marketing Body</p>',
            'partner_to': '${object.id}',
            'auto_delete': False,
        })
        
        # Create reference user who will be direct recipient
        ref_user = self.env['res.users'].create({
            'name': 'Reference User',
            'login': 'refuser@test.com',
            'email': 'refuser@test.com',
        })
        ref_partner = ref_user.partner_id

        ref_subscription = self.env['user.mail.subscription'].search([
            ('user_id', '=', ref_user.id),
            ('template_id', '=', marketing_template.id),
        ], limit=1)
        ref_subscription.write({'is_subscribed': True})
        
        # Create new user (not opted in)
        new_user = self.env['res.users'].create({
            'name': 'New User',
            'login': 'newuser2@test.com',
            'email': 'newuser2@test.com',
        })
        new_partner = new_user.partner_id
        
        # Send marketing mail to reference partner
        mail_id = marketing_template.send_mail(ref_partner.id, force_send=True)
        
        # Verify mail was NOT sent to non-opted-in new user
        mail_rec = self.env['mail.mail'].browse(mail_id)
        recipients = mail_rec.recipient_ids

        self.assertIn(ref_partner, recipients)
        self.assertNotIn(new_partner, recipients)

    def test_new_user_gets_subscription_entries_for_existing_subscribable_templates(self):
        """New users should get subscription rows for templates already subscribable."""
        informational_template = self.env['mail.template'].create({
            'name': 'Info Template Existing',
            'model_id': self.model_res_partner.id,
            'subscription_policy_id': self.informational_policy.id,
            'subject': 'Info Subject',
            'body_html': '<p>Info Body</p>',
        })
        marketing_template = self.env['mail.template'].create({
            'name': 'Marketing Template Existing',
            'model_id': self.model_res_partner.id,
            'subscription_policy_id': self.marketing_policy.id,
            'subject': 'Marketing Subject',
            'body_html': '<p>Marketing Body</p>',
        })

        new_user = self.env['res.users'].create({
            'name': 'Auto Sub User',
            'login': 'auto_sub_user@test.com',
            'email': 'auto_sub_user@test.com',
        })

        info_subscription = self.env['user.mail.subscription'].search([
            ('user_id', '=', new_user.id),
            ('template_id', '=', informational_template.id),
        ], limit=1)
        self.assertTrue(info_subscription)
        self.assertTrue(info_subscription.is_subscribed)

        marketing_subscription = self.env['user.mail.subscription'].search([
            ('user_id', '=', new_user.id),
            ('template_id', '=', marketing_template.id),
        ], limit=1)
        self.assertTrue(marketing_subscription)
        self.assertFalse(marketing_subscription.is_subscribed)