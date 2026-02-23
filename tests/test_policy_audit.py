from odoo.tests import TransactionCase, tagged


@tagged('standard', 'policy_audit')
class TestMailTemplatePolicyAudit(TransactionCase):
    """Test that policy changes are audited/tracked."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.model_res_partner = cls.env.ref('base.model_res_partner')

    def test_policy_change_is_tracked(self):
        """Changing subscription policy should be tracked."""
        # Get policies
        informational_policy = self.env['mail.subscription.policy'].search([('name', '=', 'informational')], limit=1)
        marketing_policy = self.env['mail.subscription.policy'].search([('name', '=', 'marketing')], limit=1)
        
        # Create template with informational policy
        template = self.env['mail.template'].create({
            'name': 'Audit Test Template',
            'model_id': self.model_res_partner.id,
            'subject': 'Test Subject',
            'body_html': '<p>Test Body</p>',
            'subscription_policy_id': informational_policy.id,
        })
        
        # Verify initial policy
        self.assertEqual(template.subscription_policy_id, informational_policy)
        
        # Change policy to marketing
        template.subscription_policy_id = marketing_policy.id
        
        # Verify policy changed
        self.assertEqual(template.subscription_policy_id, marketing_policy)

    def test_multiple_policy_changes_tracked(self):
        """Multiple policy changes should be persisted."""
        informational_policy = self.env['mail.subscription.policy'].search([('name', '=', 'informational')], limit=1)
        marketing_policy = self.env['mail.subscription.policy'].search([('name', '=', 'marketing')], limit=1)
        transactional_policy = self.env['mail.subscription.policy'].search([('name', '=', 'transactional')], limit=1)
        
        # Create template
        template = self.env['mail.template'].create({
            'name': 'Multi Change Audit Template',
            'model_id': self.model_res_partner.id,
            'subject': 'Test Subject',
            'body_html': '<p>Test Body</p>',
            'subscription_policy_id': informational_policy.id,
        })
        
        # Verify initial state
        self.assertEqual(template.subscription_policy_id, informational_policy)
        
        # Change to marketing
        template.subscription_policy_id = marketing_policy.id
        self.assertEqual(template.subscription_policy_id, marketing_policy)
        
        # Change to transactional
        template.subscription_policy_id = transactional_policy.id
        self.assertEqual(template.subscription_policy_id, transactional_policy)
        
        # Re-fetch to verify persistence
        template_refetch = self.env['mail.template'].browse(template.id)
        self.assertEqual(template_refetch.subscription_policy_id, transactional_policy)
