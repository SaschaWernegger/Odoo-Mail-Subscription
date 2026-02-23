from collections import OrderedDict
from typing import List, Optional
import logging

_logger = logging.getLogger(__name__)


# Registry maps policy technical name -> policy instance
_policy_registry = OrderedDict()


def register_policy(cls):
    """Decorator that instantiates and registers a policy class.

    The decorator instantiates the class and registers the instance using
    its ``name`` attribute. If instantiation fails the class is returned
    unmodified to avoid breaking imports during dev cycles.
    """
    try:
        inst = cls()
    except Exception:
        _logger.exception('Failed to instantiate policy class %s', getattr(cls, '__name__', cls))
        return cls
    if not inst.name:
        _logger.warning('Policy class %s has no name - skipping registration', getattr(cls, '__name__', cls))
        return cls
    _policy_registry[inst.name] = inst
    return cls


def get_registered_policies() -> List['BasePolicy']:
    """Return registered policy instances sorted by ``sequence``."""
    return sorted(_policy_registry.values(), key=lambda p: getattr(p, 'sequence', 0))


def get_policy(name: str) -> Optional['BasePolicy']:
    """Return a registered policy instance by technical name or None."""
    return _policy_registry.get(name)

class BasePolicy:
    """Base class for subscription policy implementations.

    Subclasses should set ``name``, ``label`` and optionally ``sequence``.
    """

    sequence = 10
    name = None
    label = None
    description = None
    options = None
    subscribable = False
    subscribed_by_default = False

    def __init__(self):
        self.sequence = getattr(self, 'sequence', 10)
        self.name = getattr(self, 'name', None)
        self.label = getattr(self, 'label', None)
        self.description = getattr(self, 'description', None)

    def valid_on(self, template) -> bool:
        """Check if this policy is valid/applicable for a template.
        
        Override in subclass if needed. Default returns True for all templates.
        """
        return True

    def filter_recipients(self, mail, env) -> List[int]:
        """Given a mail (mail.mail), return list of partner IDs who should receive it."""
        return True

    def should_filter(self, mail, env) -> bool:
        """Return whether this policy should filter recipients for the given mail.

        Subclasses can override this to skip filtering for specific delivery
        contexts (for example direct/chatter notifications).
        """
        return True

    def __repr__(self):
        return f"<Policy {self.name} ({self.label}) seq={self.sequence}>"


# Keep the registry deterministic
_policy_registry = OrderedDict((p.name, p) for p in get_registered_policies())
