"""Converge appliance resources declared in tenant vars, over HTTP.

Unlike every other operation here, this one does NOT run over SSH and does not
touch pyinfra's inventory: the targets need not be reachable by shell, and often
are not. It runs from the control node against endpoints declared in vars.

Tenant vars, both keyed by an opaque target name:

    API_TARGETS = {
        "fw-01": {
            "driver": "opnsense",
            "base_url": "https://fw-01.example.com/api",
            "verify_tls": True,            # or "ca_bundle" / "fingerprint"
            # Credentials: choose whichever source suits the tenant. Inline is
            # fine in a private tenant repo; a name is better when the repo is
            # shared more widely than the secret should be.
            "key": "...", "secret": "...",      # inline, OR:
            # "credential": "FW01",             # -> FW01_KEY/FW01_SECRET or FW01_FILE
        },
    }

    API_RESOURCES = {
        "fw-01": {
            "dhcp_reservation": [
                {"hw_address": "00:00:5e:00:53:00", "ip_address": "192.0.2.25",
                 "hostname": "printer", "subnet": "..."},
            ],
        },
    }

Where the credential comes from is the TENANT'S choice -- see
`core.api.client.credential_for`. flamelet does not require secrets to live
outside the tenant repository; that is an estate policy, not a property this
tool should enforce.
"""

from __future__ import annotations

from core.api.client import ApiClient, TlsPolicy, credential_for
from core.api.converge import converge_resource_type
from core.api.drivers import get_driver


def build_client(target_name: str, target: dict) -> ApiClient:
    """Construct a client from a tenant's target declaration."""
    missing = [k for k in ("driver", "base_url") if not target.get(k)]
    if missing:
        raise ValueError(f"API target {target_name!r} is missing: {', '.join(missing)}")

    key, secret = credential_for(target)
    tls = TlsPolicy(
        verify=target.get("verify_tls", True),
        ca_bundle=target.get("ca_bundle"),
        fingerprint=target.get("fingerprint"),
    )
    return ApiClient(
        base_url=target["base_url"],
        key=key,
        secret=secret,
        tls=tls,
        timeout=int(target.get("timeout", 20)),
    )


def converge_target(target_name: str, target: dict, resources: dict, dry: bool = True) -> list:
    """Converge every declared resource type on one target."""
    driver = get_driver(target["driver"])
    client = build_client(target_name, target)
    results = []
    for type_name, desired in (resources or {}).items():
        results.append(
            converge_resource_type(
                client,
                driver,
                type_name,
                list(desired or []),
                target=target_name,
                dry=dry,
                prune=bool(target.get("prune", False)),
            )
        )
    return results


def add_api_resource_ops(state, hosts, config, target_hosts=None, task="all", dry=True):
    """Entry point used by TASK_REGISTRY (op_type "api").

    Returns the ConvergeResults so a caller -- CLI, tests, or the web UI -- can
    render them. It prints a per-target line because a convergence run that
    reports nothing is indistinguishable from one that did nothing.
    """
    targets = getattr(config, "API_TARGETS", None) or {}
    resources = getattr(config, "API_RESOURCES", None) or {}
    if not targets:
        return []

    all_results = []
    for target_name, target in targets.items():
        try:
            results = converge_target(target_name, target, resources.get(target_name, {}), dry=dry)
        except Exception as exc:  # noqa: BLE001 - one bad target must not stop the rest
            print(f"  [api] {target_name}: ERROR {exc}")
            continue
        for result in results:
            described = result.describe()
            print(f"  [api] {described}")
            for err in result.errors:
                print(f"  [api] {target_name}: ERROR {err}")
        all_results.extend(results)
    return all_results
