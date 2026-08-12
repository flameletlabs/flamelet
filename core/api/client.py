"""HTTP transport for appliances managed through an API rather than files.

WHY THIS EXISTS
---------------
Most operations in this repo render a config file and apply it over SSH. That
assumes the target has editable files and a shell. Appliances -- firewalls,
switches, storage heads -- increasingly expose an HTTP API as the ONLY supported
management surface: config lives in a database, and editing it out-of-band is
unsupported and often silently reverted.

This module is the vendor-neutral half of managing those. It knows how to talk
HTTP safely; it knows nothing about any particular appliance. Endpoint layouts
and resource semantics belong in a driver (see core/api/drivers/).

STDLIB ONLY, DELIBERATELY
-------------------------
flamelet declares exactly one runtime dependency (pyinfra). `requests` would be
more comfortable, but adding a dependency to a tool other people install, for
one feature, is a cost paid by every user. urllib plus ssl covers everything
needed here including custom CA bundles and certificate pinning.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import socket
import ssl
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

#: Substrings that mark a value as secret. Used to redact anything echoed into
#: logs or exceptions. A leaked credential in a traceback is still a leak.
_SECRET_HINTS = ("secret", "password", "token", "key", "passphrase", "auth")


class ApiError(RuntimeError):
    """An API call failed. Carries status and a REDACTED body."""

    def __init__(self, message: str, status: Optional[int] = None, body: str = ""):
        super().__init__(message)
        self.status = status
        self.body = body


class CredentialError(RuntimeError):
    """A credential could not be resolved. Never contains the value."""


def redact(value: Any) -> Any:
    """Recursively blank anything that looks like a secret.

    Applied to request bodies before they are logged. Deliberately errs toward
    over-redaction: a redacted field that was harmless costs nothing, the
    reverse is a disclosure.
    """
    if isinstance(value, dict):
        out = {}
        for k, v in value.items():
            if any(h in str(k).lower() for h in _SECRET_HINTS):
                out[k] = "<redacted>"
            else:
                out[k] = redact(v)
        return out
    if isinstance(value, list):
        return [redact(v) for v in value]
    return value


def resolve_credential(name: str, env: Optional[dict] = None) -> tuple[str, str]:
    """Resolve an API key/secret pair from the environment or a file.

    This is ONE source among several -- see `credential_for`, which picks a
    source. Two lookups, in order:

      1. environment: ``<NAME>_KEY`` and ``<NAME>_SECRET``
      2. file named by ``<NAME>_FILE``, containing ``key`` and ``secret`` lines

    Raising rather than returning empty strings is deliberate. An empty
    credential produces a 401 later, at a point far from the actual mistake.
    """
    env = os.environ if env is None else env
    key = env.get(f"{name}_KEY")
    secret = env.get(f"{name}_SECRET")
    if key and secret:
        return key, secret

    path = env.get(f"{name}_FILE")
    if path:
        p = Path(path)
        if not p.is_file():
            raise CredentialError(f"credential {name}: {name}_FILE points at a missing file")
        pairs = {}
        for line in p.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            pairs[k.strip().lower()] = v.strip()
        if pairs.get("key") and pairs.get("secret"):
            return pairs["key"], pairs["secret"]
        raise CredentialError(f"credential {name}: file must define key= and secret=")

    raise CredentialError(
        f"credential {name} not found: set {name}_KEY and {name}_SECRET, or {name}_FILE"
    )


def credential_for(target: dict, env: Optional[dict] = None) -> tuple[str, str]:
    """Pick a credential source for one target.

    WHERE SECRETS LIVE IS THE TENANT'S CALL, NOT THIS TOOL'S
    --------------------------------------------------------
    An earlier draft mandated that values never appear in tenant vars. That was
    an opinion dressed as a requirement: tenant repositories are typically
    PRIVATE, and pushing every secret to an out-of-tree file buys nothing there
    while making every run depend on a file being present -- and a missing file
    is a silent misconfiguration at exactly the wrong moment.

    So flamelet supports several sources and takes no position on which is
    correct for a given estate:

      inline   ``{"key": ..., "secret": ...}`` in vars. Legitimate when the
               tenant repo is private, and the least machinery.
      named    ``{"credential": "NAME"}`` -> environment or a mode-0600 file.
               The right choice when the tenant repo is shared more widely than
               the secret should be, or when the value is rotated elsewhere.

    A third source -- a per-tenant vault or password store, encrypted at rest
    and possibly living in git -- is planned and deliberately not improvised
    here; it needs a design rather than a keyword.

    Whichever source is used, values are redacted from transcripts and errors.
    """
    key, secret = target.get("key"), target.get("secret")
    if key and secret:
        return key, secret
    if target.get("credential"):
        return resolve_credential(target["credential"], env=env)
    raise CredentialError(
        "no credential source: give either inline key/secret, or "
        "credential=<NAME> resolved from <NAME>_KEY/<NAME>_SECRET or <NAME>_FILE"
    )


@dataclass
class TlsPolicy:
    """How to verify the appliance's certificate.

    Appliances ship self-signed certificates, and most vendor documentation
    tells you to disable verification. Doing that on the credential that can
    rewrite a firewall ruleset is a poor default, so verification is ON here and
    the ways to cope with a self-signed cert come first:

      ca_bundle   trust a specific CA
      fingerprint pin the leaf certificate by sha256 -- the right answer for a
                  self-signed appliance, because it is verification, not the
                  absence of it
      insecure    explicit opt-out. Recorded on the object so callers can print
                  it; a silent opt-out is how this becomes permanent.
    """

    verify: bool = True
    ca_bundle: Optional[str] = None
    fingerprint: Optional[str] = None

    @property
    def insecure(self) -> bool:
        return not self.verify and not self.fingerprint

    def build_context(self) -> ssl.SSLContext:
        ctx = ssl.create_default_context()
        if self.ca_bundle:
            ctx.load_verify_locations(cafile=self.ca_bundle)
            return ctx
        if self.fingerprint:
            # Pinning replaces chain validation: we do not care who signed it,
            # we care that it is the same certificate as last time. Hostname
            # checking is off for the same reason -- a self-signed appliance
            # cert rarely carries a matching SAN.
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            return ctx
        if not self.verify:
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
        return ctx


def _normalise_fingerprint(value: str) -> str:
    return value.replace(":", "").replace(" ", "").strip().lower()


@dataclass
class ApiClient:
    """Minimal JSON-over-HTTP client with Basic auth, retry and TLS policy.

    Not a general HTTP library. It does exactly what a reconciler needs: GET
    something, POST something, fail loudly and without leaking secrets.
    """

    base_url: str
    key: str
    secret: str
    tls: TlsPolicy = field(default_factory=TlsPolicy)
    timeout: int = 20
    retries: int = 2
    backoff: float = 0.5
    #: Set by callers that want a transcript; entries are already redacted.
    transcript: list = field(default_factory=list)

    def _auth_header(self) -> str:
        key, secret = self.key, self.secret
        raw = f"{key}:{secret}".encode()
        return "Basic " + base64.b64encode(raw).decode()

    def _url(self, path: str) -> str:
        base = self.base_url.rstrip("/")
        tail = path.lstrip("/")
        return f"{base}/{tail}"

    def _verify_pin(self, url: str) -> None:
        """Compare the leaf certificate against the pinned fingerprint."""
        if not self.tls.fingerprint:
            return
        from urllib.parse import urlparse

        parsed = urlparse(url)
        host = parsed.hostname
        port = parsed.port or 443
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        with socket.create_connection((host, port), timeout=self.timeout) as sock:
            with ctx.wrap_socket(sock, server_hostname=host) as tls_sock:
                der = tls_sock.getpeercert(binary_form=True)
        actual = hashlib.sha256(der).hexdigest()
        expected = _normalise_fingerprint(self.tls.fingerprint)
        if actual != expected:
            raise ApiError(
                "certificate fingerprint mismatch: the appliance is not the host "
                "this target was pinned to (expected "
                f"{expected[:16]}..., got {actual[:16]}...)"
            )

    def request(self, path: str, payload: Optional[dict] = None) -> Any:
        """GET when payload is None, POST otherwise. Returns decoded JSON.

        Retries only on transport errors and 5xx. A 4xx is a statement about the
        request and repeating it unchanged just asks the same wrong question
        again.
        """
        url = self._url(path)
        self._verify_pin(url)
        data = None
        headers = {"Authorization": self._auth_header(), "Accept": "application/json"}
        if payload is not None:
            data = json.dumps(payload).encode()
            headers["Content-Type"] = "application/json"

        self.transcript.append(
            {
                "path": path,
                "method": "POST" if payload is not None else "GET",
                "payload": redact(payload) if payload is not None else None,
            }
        )

        ctx = self.tls.build_context()
        last: Optional[Exception] = None
        for attempt in range(self.retries + 1):
            req = urllib.request.Request(url, data=data, headers=headers)
            try:
                with urllib.request.urlopen(req, timeout=self.timeout, context=ctx) as resp:
                    body = resp.read().decode() or "{}"
                    try:
                        return json.loads(body)
                    except json.JSONDecodeError as exc:
                        raise ApiError(
                            f"{path}: response was not JSON", resp.status, body[:200]
                        ) from exc
            except urllib.error.HTTPError as exc:
                body = exc.read().decode(errors="replace")[:500]
                status = exc.code
                if status < 500:
                    raise ApiError(f"{path}: HTTP {status}", status, body) from exc
                last = ApiError(f"{path}: HTTP {status}", status, body)
            except (urllib.error.URLError, TimeoutError, socket.timeout) as exc:
                kind = type(exc).__name__
                last = ApiError(f"{path}: {kind}")
            if attempt < self.retries:
                time.sleep(self.backoff * (2**attempt))
        raise last if last else ApiError(f"{path}: request failed")

    def get(self, path: str) -> Any:
        return self.request(path)

    def post(self, path: str, payload: Optional[dict] = None) -> Any:
        return self.request(path, payload if payload is not None else {})
