"""Policies package for my_mail.

This package exposes the registry API used by the rest of the module while
keeping policy implementations split into separate modules for clarity and
testability. Importing this package will import the individual policy
modules which register themselves via the decorator in ``base``.
"""
from .base import (
    BasePolicy,
    register_policy,
    get_registered_policies,
    get_policy,
)

# Import policy implementations so they register at import time
from . import informational  # noqa: F401
from . import marketing  # noqa: F401
from . import transactional  # noqa: F401

__all__ = [
    'BasePolicy',
    'register_policy',
    'get_registered_policies',
    'get_policy',
]
