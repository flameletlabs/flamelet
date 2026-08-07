"""Tests for the pure service-config renderers.

monit, opensmtpd, nginx, prometheus and registry all render a config file from
a spec dict. The interesting ones take a PATH argument — conf_dir, storage_path,
state_dir — because those differ per OS, and a path assembled wrong produces a
perfectly valid config written to a place nothing reads.

monit._generate_monitrc gained its state_dir parameter in the change that
stopped hardcoding /var/lib/monit; that parameter had no test until now.

Assertions target directives, not whole-file equality.
"""

import pytest

from core.operations.monit import _generate_monit_config, _generate_monitrc
from core.operations.nginx import _generate_nginx_config
from core.operations.opensmtpd import _generate_smtpd_conf, _generate_smtpd_config
from core.operations.prometheus import _generate_alert_rules, _generate_prometheus_yml
from core.operations.registry import _generate_compose_yml, _generate_registry_config


class TestMonitStateDir:
    """The parameter that exists precisely because the path differs per OS."""

    @pytest.mark.parametrize("state_dir", ["/var/lib/monit", "/var/monit"])
    def test_idfile_and_statefile_follow_state_dir(self, state_dir):
        text = _generate_monitrc({}, state_dir=state_dir)
        assert f"set idfile {state_dir}/monit.id" in text
        assert f"set statefile {state_dir}/monit.state" in text

    def test_default_is_the_linux_location(self):
        assert "set idfile /var/lib/monit/monit.id" in _generate_monitrc({})

    def test_state_files_are_not_written_under_root(self):
        """They were moved off /root because it is read-only on some hosts."""
        for state_dir in ("/var/lib/monit", "/var/monit"):
            assert "/root/" not in _generate_monitrc({}, state_dir=state_dir)

    def test_daemon_interval_default_and_override(self):
        assert "set daemon 120" in _generate_monitrc({})
        assert "set daemon 30" in _generate_monitrc({"daemon": 30})

    def test_convenience_wrapper_cannot_reach_the_bsd_path(self):
        """_generate_monit_config takes a hostname it never uses and calls
        _generate_monitrc WITHOUT state_dir, so it always renders the Linux
        location. Pinned as current behaviour: any caller needing the BSD path
        must use _generate_monitrc directly."""
        assert _generate_monit_config({}, hostname="host.example.com") == _generate_monitrc({})
        assert "/var/lib/monit" in _generate_monit_config({})


class TestMonitContent:
    def test_mmonit_url_is_optional(self):
        assert "mmonit" not in _generate_monitrc({}).lower()
        text = _generate_monitrc({"mmonit_url": "https://monit.example.com/collector"})
        assert "https://monit.example.com/collector" in text

    def test_checks_are_emitted(self):
        text = _generate_monitrc(
            {"checks": {"system": "check system host.example.com\n  if memory > 75% then alert"}}
        )
        assert "check system host.example.com" in text


class TestOpensmtpdPaths:
    @pytest.mark.parametrize("conf_dir", ["/etc/mail", "/usr/local/etc/mail", "/etc/smtpd"])
    def test_table_paths_follow_conf_dir(self, conf_dir):
        """conf_dir differs per OS; a wrong path yields a config that loads and
        then cannot find its tables."""
        text = _generate_smtpd_conf({}, conf_dir)
        assert f"table aliases file:{conf_dir}/aliases" in text

    def test_secrets_table_only_when_declared(self):
        assert "secrets" not in _generate_smtpd_conf({}, "/etc/mail")
        text = _generate_smtpd_conf({"tables": {"secrets": {}}}, "/etc/mail")
        assert "table secrets file:/etc/mail/secrets" in text

    def test_mynetworks_table_only_when_declared(self):
        assert "mynetworks" not in _generate_smtpd_conf({}, "/etc/mail")
        text = _generate_smtpd_conf({"allowed_networks": ["10.0.0.0/24"]}, "/etc/mail")
        assert "table mynetworks file:/etc/mail/mynetworks" in text

    def test_relay_host_and_auth_only_when_a_relay_is_configured(self):
        """Both branches emit an "outbound" action — without a relay host the
        MTA delivers directly, which is intentional. Only the host/auth part is
        conditional."""
        direct = _generate_smtpd_conf({}, "/etc/mail")
        assert 'action "outbound" relay' in direct
        # "relay host", not bare "host " — the latter also matches "localhost"
        # in the listener line.
        assert "relay host" not in direct
        assert "auth <secrets>" not in direct

        relayed = _generate_smtpd_conf(
            {"smtp_relay": "smtp.example.com:587", "mail_from": "alerts@example.com"}, "/etc/mail"
        )
        assert "host smtp.example.com:587" in relayed
        assert "auth <secrets>" in relayed
        assert "alerts@example.com" in relayed

    @pytest.mark.parametrize(
        "config", [{}, {"smtp_relay": "smtp.example.com:587"}], ids=["direct", "relayed"]
    )
    def test_absent_mail_from_omits_the_clause_entirely(self, config):
        """It used to interpolate unconditionally and render the literal
        mail-from "None" — not a valid envelope sender, and smtpd loads the
        file happily so it only surfaced when mail bounced."""
        text = _generate_smtpd_conf(config, "/etc/mail")
        assert 'mail-from "None"' not in text
        assert "mail-from" not in text

    def test_present_mail_from_is_still_emitted(self):
        """Control: the omission must be conditional, not unconditional."""
        text = _generate_smtpd_conf({"mail_from": "alerts@example.com"}, "/etc/mail")
        assert 'mail-from "alerts@example.com"' in text

    def test_listeners_are_always_present(self):
        text = _generate_smtpd_conf({}, "/etc/mail")
        assert "listen on socket" in text
        assert "listen on localhost port 25" in text

    def test_convenience_wrapper_delegates(self):
        assert isinstance(_generate_smtpd_config({}), str)


class TestPrometheus:
    def test_scrape_interval_default_and_override(self):
        assert "scrape_interval: 15s" in _generate_prometheus_yml({}, "/etc/prometheus")
        assert "scrape_interval: 30s" in _generate_prometheus_yml(
            {"scrape_interval": "30s"}, "/etc/prometheus"
        )

    def test_alerting_block_only_when_rules_exist(self):
        assert "alerting:" not in _generate_prometheus_yml({}, "/etc/prometheus")
        text = _generate_prometheus_yml(
            {"alert_rules": [{"alert": "Down", "expr": "up == 0"}]}, "/etc/prometheus"
        )
        assert "alerting:" in text

    def test_alert_rule_defaults(self):
        """for/severity/summary all default; description defaults to empty."""
        text = _generate_alert_rules([{"alert": "InstanceDown", "expr": "up == 0"}])
        assert "- alert: InstanceDown" in text
        assert "expr: up == 0" in text
        assert "for: 5m" in text
        assert "severity: warning" in text
        assert 'summary: "InstanceDown"' in text

    def test_alert_rule_overrides(self):
        text = _generate_alert_rules(
            [
                {
                    "alert": "DiskFull",
                    "expr": "disk > 90",
                    "for": "10m",
                    "severity": "critical",
                    "summary": "Disk nearly full",
                    "description": "Above 90 percent",
                }
            ]
        )
        assert "for: 10m" in text
        assert "severity: critical" in text
        assert 'summary: "Disk nearly full"' in text
        assert 'description: "Above 90 percent"' in text

    def test_empty_rule_list_still_produces_a_valid_group(self):
        text = _generate_alert_rules([])
        assert "groups:" in text
        assert "rules:" in text


class TestRegistryCompose:
    SPEC = {"version": "2.8"}

    @pytest.mark.parametrize("storage", ["/var/lib/registry", "/srv/registry"])
    def test_volumes_follow_storage_path(self, storage):
        text = _generate_compose_yml(self.SPEC, storage, 5000)
        assert f"- {storage}/data:/var/lib/registry" in text
        assert f"- {storage}/config.yml:/etc/docker/registry/config.yml:ro" in text

    def test_listen_port_maps_to_container_5000(self):
        assert "- '5443:5000'" in _generate_compose_yml(self.SPEC, "/srv/registry", 5443)

    def test_image_version_default_and_override(self):
        assert "image: registry:2.8" in _generate_compose_yml({}, "/srv/registry", 5000)
        assert "image: registry:2.9" in _generate_compose_yml(
            {"version": "2.9"}, "/srv/registry", 5000
        )

    def test_auth_volume_only_for_htpasswd(self):
        without = _generate_compose_yml(self.SPEC, "/srv/registry", 5000)
        assert "/auth:ro" not in without
        with_auth = _generate_compose_yml(
            {**self.SPEC, "auth": {"type": "htpasswd"}}, "/srv/registry", 5000
        )
        assert "- /srv/registry/auth:/auth:ro" in with_auth

    def test_registry_config_renders(self):
        assert isinstance(_generate_registry_config(self.SPEC, "/srv/registry"), str)


class TestNginx:
    def test_base_http_block_is_present(self):
        text = _generate_nginx_config({})
        assert "events {" in text
        assert "http {" in text
        assert "worker_connections 1024;" in text

    @pytest.mark.parametrize("conf_dir", ["/etc/nginx", "/usr/local/etc/nginx"])
    def test_mime_types_include_follows_conf_dir(self, conf_dir):
        """FreeBSD keeps nginx under /usr/local/etc; a hardcoded path would
        write a valid config that cannot find mime.types."""
        assert f"include {conf_dir}/mime.types;" in _generate_nginx_config({}, conf_dir)

    def test_upstreams_render_server_entries(self):
        text = _generate_nginx_config(
            {"upstreams": [{"name": "api", "servers": ["127.0.0.1:8080", "127.0.0.1:8081"]}]}
        )
        assert "upstream api {" in text
        assert "server 127.0.0.1:8080;" in text
        assert "server 127.0.0.1:8081;" in text

    def test_listen_accepts_a_list_of_ports(self):
        text = _generate_nginx_config({"servers": [{"listen": [80, 8080]}]})
        assert "listen 80;" in text
        assert "listen 8080;" in text

    def test_port_443_implies_ssl_and_http2(self):
        """443 is special-cased — the directive is not bare."""
        text = _generate_nginx_config({"servers": [{"listen": [443]}]})
        assert "listen 443 ssl http2;" in text
        assert "listen 443;" not in text

    def test_listen_defaults_to_80(self):
        assert "listen 80;" in _generate_nginx_config({"servers": [{}]})

    def test_listen_accepts_a_bare_string_like_the_docs_show(self):
        """A string used to be walked character by character: "80" rendered as
        `listen 8;` plus `listen 0;`."""
        text = _generate_nginx_config({"servers": [{"listen": "80"}]})
        assert "listen 80;" in text
        assert "listen 8;" not in text
        assert "listen 0;" not in text

    def test_listen_accepts_a_bare_int(self):
        assert "listen 8080;" in _generate_nginx_config({"servers": [{"listen": 8080}]})

    def test_documented_plural_upstreams_key_is_honoured(self):
        text = _generate_nginx_config(
            {"upstreams": [{"name": "api", "servers": ["127.0.0.1:8080"]}]}
        )
        assert "upstream api {" in text

    def test_singular_upstream_key_is_rejected_not_silently_dropped(self):
        """It was previously ignored, leaving every proxy_pass referencing it
        unresolvable at runtime — far harder to diagnose than a failed deploy."""
        with pytest.raises(ValueError) as exc:
            _generate_nginx_config({"upstream": [{"name": "api", "servers": ["127.0.0.1:8080"]}]})
        assert "upstreams" in str(exc.value)

    def test_plural_wins_when_both_are_present(self):
        text = _generate_nginx_config(
            {
                "upstreams": [{"name": "api", "servers": ["127.0.0.1:8080"]}],
                "upstream": [{"name": "ignored", "servers": ["127.0.0.1:9999"]}],
            }
        )
        assert "upstream api {" in text
        assert "ignored" not in text
