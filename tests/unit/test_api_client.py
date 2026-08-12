"""Client tests: credentials never inline, secrets never logged, TLS not off by default."""

import ssl

import pytest

from core.api.client import CredentialError, TlsPolicy, redact, resolve_credential

# -- credentials ---------------------------------------------------------


def test_credential_from_environment():
    env = {"FW_KEY": "k", "FW_SECRET": "s"}
    assert resolve_credential("FW", env=env) == ("k", "s")


def test_credential_from_file(tmp_path):
    f = tmp_path / "cred"
    f.write_text("# comment\nkey = abc\nsecret = def\n")
    assert resolve_credential("FW", env={"FW_FILE": str(f)}) == ("abc", "def")


def test_missing_credential_raises_naming_what_to_set():
    """An empty credential would surface as a 401 far from the mistake."""
    with pytest.raises(CredentialError, match="FW_KEY"):
        resolve_credential("FW", env={})


def test_credential_file_that_does_not_exist_is_an_error(tmp_path):
    with pytest.raises(CredentialError, match="missing file"):
        resolve_credential("FW", env={"FW_FILE": str(tmp_path / "nope")})


def test_incomplete_credential_file_is_an_error(tmp_path):
    f = tmp_path / "cred"
    f.write_text("key = abc\n")
    with pytest.raises(CredentialError, match="key= and secret="):
        resolve_credential("FW", env={"FW_FILE": str(f)})


def test_error_never_contains_the_secret_value():
    env = {"FW_KEY": "k"}  # secret missing
    try:
        resolve_credential("FW", env=env)
    except CredentialError as exc:
        assert "k" not in str(exc).replace("FW_KEY", "").replace("FW_SECRET", "")


# -- redaction -----------------------------------------------------------


@pytest.mark.parametrize("field", ["secret", "password", "api_token", "Key", "authorization"])
def test_secret_shaped_fields_are_redacted(field):
    assert redact({field: "hunter2"})[field] == "<redacted>"


def test_redaction_is_recursive_and_keeps_harmless_values():
    out = redact({"outer": {"password": "p", "name": "GW_A"}, "list": [{"token": "t"}]})
    assert out["outer"]["password"] == "<redacted>"
    assert out["outer"]["name"] == "GW_A"
    assert out["list"][0]["token"] == "<redacted>"


# -- TLS -----------------------------------------------------------------


def test_verification_is_on_by_default():
    """Vendor docs routinely say to disable this. Not the default here."""
    policy = TlsPolicy()
    assert policy.verify is True
    assert policy.insecure is False
    ctx = policy.build_context()
    assert ctx.verify_mode == ssl.CERT_REQUIRED
    assert ctx.check_hostname is True


def test_disabling_verification_is_visible_as_insecure():
    assert TlsPolicy(verify=False).insecure is True


def test_pinning_is_not_insecure_even_though_chain_checking_is_off():
    """Pinning is verification, not the absence of it.

    A self-signed appliance cert has no valid chain and rarely a matching SAN,
    so pinning the leaf is the correct answer rather than turning checks off.
    """
    policy = TlsPolicy(verify=False, fingerprint="AA:BB")
    assert policy.insecure is False


def test_ca_bundle_keeps_full_verification(tmp_path):
    ca = tmp_path / "ca.pem"
    ca.write_text(
        ssl.get_default_verify_paths().cafile
        and open(ssl.get_default_verify_paths().cafile).read()
        or ""
    )
    if not ca.read_text().strip():
        pytest.skip("no system CA bundle available to copy")
    ctx = TlsPolicy(ca_bundle=str(ca)).build_context()
    assert ctx.verify_mode == ssl.CERT_REQUIRED


# -- credential source selection -----------------------------------------
# Where a secret lives is the tenant's decision. flamelet supports several
# sources and mandates none; an earlier draft required out-of-tree values,
# which was an estate policy dressed as a tool requirement.


def test_inline_credential_is_supported():
    """Legitimate when the tenant repo is private."""
    from core.api.client import credential_for

    assert credential_for({"key": "k", "secret": "s"}) == ("k", "s")


def test_named_credential_still_resolves_from_environment(monkeypatch):
    from core.api.client import credential_for

    monkeypatch.setenv("FW_KEY", "ek")
    monkeypatch.setenv("FW_SECRET", "es")
    assert credential_for({"credential": "FW"}) == ("ek", "es")


def test_inline_wins_when_both_are_given():
    """Explicit beats indirect: no surprise lookup when a value is right there."""
    from core.api.client import credential_for

    assert credential_for({"key": "k", "secret": "s", "credential": "FW"}) == ("k", "s")


def test_no_credential_source_at_all_names_both_options():
    from core.api.client import credential_for

    with pytest.raises(CredentialError, match="inline key/secret"):
        credential_for({})
