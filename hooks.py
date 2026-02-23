"""Initialize module and set up database policies."""

import logging

_logger = logging.getLogger(__name__)


def _register_policies(cr, registry):
    """Create or update subscription policy records from policy classes.
    
    This is called from post_init_hook to populate mail.subscription.policy
    with records based on registered policy classes.
    
    Args:
        cr: Database cursor
        registry: Model registry
    """
    try:
        _logger.info("[my_mail] Starting policy registration...")
        from . import policies
        from odoo.api import Environment
        import odoo
        
        env = Environment(cr, odoo.SUPERUSER_ID, {})
        policy_model = env['mail.subscription.policy']
        
        # Get all registered policy classes
        registered = policies.get_registered_policies()
        _logger.info(f"[my_mail] Found {len(registered)} registered policies")
        
        for policy_cls in registered:
            _logger.debug(f"[my_mail] Processing policy: {policy_cls.name}")
            # Create or update record based on policy class
            existing = policy_model.search([('name', '=', policy_cls.name)], limit=1)
            
            values = {
                'sequence': policy_cls.sequence,
                'name': policy_cls.name,
                'label': policy_cls.label,
                'description': policy_cls.description or '',
            }
            
            if existing:
                existing.write(values)
                _logger.info(f"[my_mail] ✓ Updated policy: {policy_cls.name}")
            else:
                policy_model.create(values)
                _logger.info(f"[my_mail] ✓ Created policy: {policy_cls.name}")
        
        # Commit transaction to ensure policies are persisted
        cr.commit()
        _logger.info(f"[my_mail] ✓ All {len(registered)} policies registered successfully")
    
    except Exception as e:
        _logger.error(f"[my_mail] Error registering policies: {e}", exc_info=True)
        raise


def post_init_hook(env):
    """Execute after module installation.
    
    This hook is called after all models and data have been loaded.
    We use this to register policies.
    
    Args:
        env: Environment object (contains cr and registry)
    """
    _register_policies(env.cr, env.registry)
