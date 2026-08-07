"""Detection of private infrastructure in repository content.

flamelet is a public repository (see the MANDATORY section at the top of
CLAUDE.md). This module holds the patterns and allowlists; two things consume
it, and they MUST share this code rather than each keeping a copy:

  tests/unit/test_no_private_infrastructure.py   runs in CI, over tracked files
  scripts/pre_commit_privacy_scan.py             runs before a commit exists

A second copy of these patterns would drift from the first, and the drifted one
would be the one reporting CLEAN.

WHY BOTH LAYERS EXIST
---------------------
CI runs after the commit object exists, so it catches a leak only once the
hostname is already permanent in history — sanitizing the tip afterwards does
not remove it. The pre-commit hook stops it entering history at all. CI remains
the backstop, because a hook can be skipped with --no-verify and is not
installed in a fresh clone until someone runs `make hooks`.

Every check carries a planted positive in the test module. A probe that cannot
fire reports CLEAN forever; this repo has been bitten by that four separate
ways (git grep -E and BSD sed both silently ignoring \\b, gh api printing its
404 to stdout, and a hand-written pattern that enumerated hostnames instead of
matching their shape).
"""

import re
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

# Paths that are exempt, each for a reason that has been verified:
EXEMPT_PREFIXES = (
    # A deliberately fictional example tenant. Generic addresses are the point.
    "tenants/flamelet-example/",
    # Vendored/minified third-party JS and build output. Not authored here, and
    # a source of false positives: lunr's Dutch stemmer contains a literal that
    # reads as a hostname label (it is a Dutch suffix), and RxJS bundles
    # contain attribute accesses that match the same shape.
    "assets/",
    "web/dist/",
    "site/",
)

# Registrable domains that may legitimately appear: documentation examples
# (RFC 2606) plus real third-party services the framework talks to.
APPROVED_DOMAINS = {
    "example.com",
    "example.net",
    "example.org",
    "example.local",
    "netbird.io",
    "jsdelivr.net",
    "debian.org",
    "googleapis.com",
    "k3s.io",
    "githubusercontent.com",
    "npmjs.org",
    "freedesktop.org",
    "openstreetmap.org",
    "github.com",
    "gnu.org",
    "python.org",
    "conf.local",  # matches the filename rc.conf.local, not a host
}

FQDN_RE = re.compile(
    r"\b[a-z0-9](?:[a-z0-9-]*[a-z0-9])?(?:\.[a-z0-9-]+)+"
    r"\.(?:com|net|org|io|dev|sh|internal|local|lan|invalid|test)\b"
)


def _fqdn_violations(text):
    out = []
    for m in FQDN_RE.finditer(text):
        host = m.group(0)
        registrable = ".".join(host.split(".")[-2:])
        if registrable not in APPROVED_DOMAINS:
            out.append(host)
    return out


def _private_ipv4_violations(text):
    """192.168.x.y with an unusual third octet, and any 172.16-31.x.y.

    NOT flagged: 10.0.0.0/8, which this repo uses throughout as its
    documentation address convention, so flagging it would make the check
    unusable. 192.168.0/1.x are the ubiquitous consumer-router defaults and
    carry no information about anyone's network. A third octet outside those
    is how a real site network looks — which is what leaked last time.
    """
    out = []
    for m in re.finditer(r"\b192\.168\.(\d{1,3})\.\d{1,3}\b", text):
        if m.group(1) not in ("0", "1"):
            out.append(m.group(0))
    out += re.findall(r"\b172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3}\b", text)
    return out


def _cgnat_violations(text):
    """Tailscale node IPs in 100.64.0.0/10.

    Allowed: 100.100.100.100 (Tailscale's *public* MagicDNS resolver, the same
    for every network) and 100.64.0.0/24, which this repo uses as its
    placeholder range the way RFC 5737 reserves 192.0.2.0/24. Real node
    addresses are scattered across the whole /10, so anything else is suspect.
    """
    out = []
    for m in re.finditer(r"\b100\.(?:6[4-9]|[7-9]\d|1[01]\d|12[0-7])\.\d{1,3}\.\d{1,3}\b", text):
        ip = m.group(0)
        if ip == "100.100.100.100" or ip.startswith("100.64.0."):
            continue
        out.append(ip)
    return out


def _home_path_violations(text):
    """/home/<user>/ paths. /home/debian is the standard Debian cloud user."""
    return [
        m.group(0)
        for m in re.finditer(r"/home/([a-z][a-z0-9_-]*)", text)
        if m.group(1) not in ("debian", "runner", "user")
    ]


def _email_violations(text):
    out = []
    for m in re.finditer(r"\b[a-zA-Z0-9._%+-]+@([a-zA-Z0-9.-]+\.[a-z]{2,})\b", text):
        domain = m.group(1)
        if domain.endswith(("example.com", "example.net", "example.org")):
            continue
        if m.group(0) == "noreply@anthropic.com":
            continue
        out.append(m.group(0))
    return out


# ---------------------------------------------------------------------------
# Private-TLD hostnames. THIS IS THE CHECK THAT MATTERS MOST.
#
# The leak that escaped the 2026-08-06 remediation was a host under a PRIVATE,
# non-ICANN TLD. A public-TLD check cannot see one, because such a TLD is not
# resolvable by anyone. So this inverts the test: every trailing label must be
# on the list below, and anything unrecognised FAILS.
#
# Failing closed is deliberate. A newly introduced private TLD trips it
# immediately, which is precisely what did not happen last time. The cost is that genuinely new
# vocabulary — a new dict key inside an f-string, a new file extension — also
# trips it. That is a one-line fix here, and it is the right trade: the
# alternative failed silently and cost a full history rewrite.
# ---------------------------------------------------------------------------
ALLOWED_TRAILING_LABELS = {
    # -- documentation / reserved domains (RFC 2606, RFC 6761) --
    "com",
    "net",
    "org",
    "io",
    "example",
    "internal",
    "local",
    "invalid",
    "test",
    # -- real third-party services the framework talks to --
    "debian",
    "freedesktop",
    "googleapis",
    "jsdelivr",
    "netbird",
    "npmjs",
    "cloud",
    "git",
    "github",
    "python",
    # -- placeholder LOCATION labels used throughout the docs and example
    #    tenant. Same shape as a private TLD, which is exactly why they are
    #    listed explicitly rather than pattern-matched. --
    "london",
    "newyork",
    "tokyo",
    "paris",
    "madrid",
    "prod",
    "production",
    # -- file extensions --
    "db",
    "bak",
    "cjs",
    "conf",
    "css",
    "gpg",
    "html",
    "img",
    "iso",
    "js",
    "json",
    "key",
    "log",
    "pem",
    "pid",
    "pub",
    # ".bin" is a file extension; "sys.executable" and a git config key
    # like "user.email" are attribute/key names, not hostnames.
    "bin",
    "executable",
    "email",
    # bhyve disk images are .raw (e.g. debian.raw) - a file extension.
    "raw",
    "py",
    "sh",
    "tgz",
    "toml",
    "yaml",
    "yml",
    # -- attribute and dict-key names that appear inside f-strings/comments,
    #    e.g. "{host.name}". Not hostnames. --
    "address",
    "api",
    "append",
    "cli",
    "common",
    "dest",
    "disable",
    "dry",
    "edges",
    "get",
    "groups",
    "host",
    "hostname",
    "hosts",
    "id",
    "inventory",
    "items",
    "keys",
    "leases",
    "length",
    "limit",
    "list",
    "location",
    "locations",
    "name",
    "nodes",
    "operations",
    "os",
    "other",
    "prestart",
    "put",
    "rules",
    "service",
    "services",
    "shell",
    "split",
    "state",
    # "ups.status" appears in docker.py prose: an attribute name, not a host.
    "status",
    "swappiness",
    "sysvipc",
    "target",
    "task",
    "tasks",
    "tenant",
    "text",
    "textfile",
    "tld",
    "type",
    "types",
}

# Hostnames hide in quoted strings, comments and prose — not in bare code, where
# a.b is attribute access. Scanning only those contexts keeps the noise down.
_STRING_OR_COMMENT = re.compile(r'"([^"\n]*)"|\'([^\'\n]*)\'|#([^\n]*)|//([^\n]*)')
_DOTTED = re.compile(r"\b[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.([a-z]{2,12})\b")


def _private_tld_violations(text, markdown=False):
    chunks = (
        [text]
        if markdown
        else [g for m in _STRING_OR_COMMENT.finditer(text) for g in m.groups() if g]
    )
    return [
        m.group(0)
        for chunk in chunks
        for m in _DOTTED.finditer(chunk)
        if m.group(1) not in ALLOWED_TRAILING_LABELS
    ]


SECRET_RE = re.compile(
    r"BEGIN (?:RSA |OPENSSH |EC |DSA |PGP )?PRIVATE KEY"
    r"|ghp_[A-Za-z0-9]{20,}"
    r"|github_pat_[A-Za-z0-9_]{20,}"
    r"|AKIA[0-9A-Z]{16}"
    r"|xox[baprs]-[A-Za-z0-9-]{10,}"
)

# name -> (finder(text, is_markdown), planted positive)
#
# Every planted positive is assembled from fragments at import time so the
# literal never appears in this file — that keeps this file inside the scan
# instead of needing an exemption, which would make it a blind spot.
CHECKS = {
    "private-ipv4": (
        lambda t, md=False: _private_ipv4_violations(t),
        "addr " + "192.168." + "150.2 here",
    ),
    "tailscale-cgnat": (
        lambda t, md=False: _cgnat_violations(t),
        "peer " + "100.89." + "149.47 here",
    ),
    "ts-net-hostname": (
        lambda t, md=False: re.findall(r"\b[a-z0-9-]+\.ts\.net\b", t),
        "host " + "virt-01-site" + ".ts" + ".net here",
    ),
    "foreign-fqdn": (
        lambda t, md=False: _fqdn_violations(t),
        "see " + "gateway" + ".acme" + ".io for details",
    ),
    "private-tld-hostname": (
        _private_tld_violations,
        '"' + "gateway" + ".corpnet" + '"',
    ),
    "home-path": (
        lambda t, md=False: _home_path_violations(t),
        "path " + "/home/" + "syseng/.config here",
    ),
    "email": (
        lambda t, md=False: _email_violations(t),
        "mail " + "someone@ex" + "ample" + "corp" + ".co here",
    ),
    "secret": (
        lambda t, md=False: SECRET_RE.findall(t),
        "-----BEGIN " + "RSA PRIVATE" + " KEY-----",
    ),
}


def tracked_text_files():
    """Every tracked file that is not exempt and is readable as text."""
    out = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    for rel in filter(None, out.split("\0")):
        if rel.startswith(EXEMPT_PREFIXES):
            continue
        path = REPO_ROOT / rel
        try:
            yield rel, path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, FileNotFoundError, IsADirectoryError):
            continue  # binary or gone; nothing text-scannable to check
