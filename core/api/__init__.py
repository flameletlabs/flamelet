"""Generic HTTP API management for appliances without editable config files."""

from core.api.client import ApiClient, ApiError, CredentialError, TlsPolicy, resolve_credential
from core.api.reconcile import Action, FieldChange, Plan, build_plan, diff_resource

__all__ = [
    "ApiClient",
    "ApiError",
    "CredentialError",
    "TlsPolicy",
    "resolve_credential",
    "Action",
    "FieldChange",
    "Plan",
    "build_plan",
    "diff_resource",
]
