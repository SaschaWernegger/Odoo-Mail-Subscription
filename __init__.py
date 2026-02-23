# Initialize the module
from . import policies  # Register policies via decorator
from . import models
from . import hooks  # Load database trigger hooks

# Expose post_init_hook at module level for Odoo installer
post_init_hook = hooks.post_init_hook
