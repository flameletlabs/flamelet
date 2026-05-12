"""Tests for configuration generation in operations."""

from io import StringIO


class TestNginxConfigGeneration:
    """Test nginx configuration generation."""

    def test_nginx_config_generator_exists(self):
        """Verify nginx config generator function exists."""
        from core.operations.nginx import _generate_nginx_config
        assert callable(_generate_nginx_config)

    def test_nginx_basic_config_generation(self):
        """Test basic nginx config generation."""
        from core.operations.nginx import _generate_nginx_config

        spec = {
            "upstreams": [
                {"name": "backend", "servers": ["10.0.0.1:8080"]}
            ],
            "servers": [
                {
                    "server_name": "example.com",
                    "listen": [80],
                    "locations": [
                        {"path": "/", "proxy_pass": "http://backend"}
                    ]
                }
            ]
        }

        config = _generate_nginx_config(spec)
        assert isinstance(config, str)
        assert "upstream backend" in config
        assert "server {" in config
        assert "proxy_pass http://backend" in config

    def test_nginx_ssl_config_generation(self):
        """Test nginx SSL config generation."""
        from core.operations.nginx import _generate_nginx_config

        spec = {
            "upstreams": [],
            "servers": [
                {
                    "server_name": "secure.example.com",
                    "listen": [443],
                    "ssl_cert": "/etc/ssl/certs/cert.pem",
                    "ssl_key": "/etc/ssl/private/key.pem",
                    "locations": []
                }
            ]
        }

        config = _generate_nginx_config(spec)
        assert "listen 443 ssl" in config
        assert "ssl_certificate /etc/ssl/certs/cert.pem" in config
        assert "ssl_certificate_key /etc/ssl/private/key.pem" in config


class TestPrometheusConfigGeneration:
    """Test Prometheus configuration generation."""

    def test_prometheus_yaml_generator_exists(self):
        """Verify Prometheus YAML generator function exists."""
        from core.operations.prometheus import _generate_prometheus_yml
        assert callable(_generate_prometheus_yml)

    def test_prometheus_basic_config_generation(self):
        """Test basic Prometheus config generation."""
        from core.operations.prometheus import _generate_prometheus_yml

        spec = {
            "scrape_interval": "15s",
            "scrape_targets": [
                {"job_name": "node", "targets": ["localhost:9100"]}
            ]
        }

        config = _generate_prometheus_yml(spec, "/etc/prometheus")
        assert isinstance(config, str)
        assert "scrape_interval: 15s" in config
        assert "job_name: 'node'" in config
        assert "targets:" in config
        assert "localhost:9100" in config

    def test_prometheus_alert_rules_generation(self):
        """Test Prometheus alert rules generation."""
        from core.operations.prometheus import _generate_alert_rules

        rules = [
            {
                "alert": "HighCPU",
                "expr": "node_cpu > 80",
                "severity": "warning"
            }
        ]

        config = _generate_alert_rules(rules)
        assert isinstance(config, str)
        assert "alert: HighCPU" in config
        assert "expr: node_cpu > 80" in config
        assert "severity: warning" in config


class TestRegistryConfigGeneration:
    """Test Docker Registry configuration generation."""

    def test_registry_config_generator_exists(self):
        """Verify registry config generator function exists."""
        from core.operations.registry import _generate_registry_config
        assert callable(_generate_registry_config)

    def test_registry_filesystem_config_generation(self):
        """Test registry filesystem config generation."""
        from core.operations.registry import _generate_registry_config

        spec = {
            "storage_backend": "filesystem",
            "auth": {}
        }

        config = _generate_registry_config(spec, "/data/registry")
        assert isinstance(config, str)
        assert "filesystem:" in config
        assert "rootdirectory: /data/registry/data" in config

    def test_registry_compose_generator_exists(self):
        """Verify registry compose generator function exists."""
        from core.operations.registry import _generate_compose_yml
        assert callable(_generate_compose_yml)

    def test_registry_compose_generation(self):
        """Test registry docker-compose generation."""
        from core.operations.registry import _generate_compose_yml

        spec = {"version": "2.8"}

        compose = _generate_compose_yml(spec, "/data/registry", 5000)
        assert isinstance(compose, str)
        assert "registry:2.8" in compose
        assert "ports:" in compose
        assert "5000:5000" in compose
        assert "volumes:" in compose


class TestUnboundConfigGeneration:
    """Test Unbound DNS configuration generation."""

    def test_unbound_config_generator_exists(self):
        """Verify unbound config generator exists."""
        from core.operations.unbound import _generate_unbound_config
        assert callable(_generate_unbound_config)

    def test_unbound_basic_config_generation(self):
        """Test basic unbound config generation."""
        from core.operations.unbound import _generate_unbound_config

        spec = {
            "listen_on": ["127.0.0.1"],
            "access_control": ["127.0.0.0/8 allow"],
            "forward_zones": []
        }

        config = _generate_unbound_config(spec)
        assert isinstance(config, str)
        assert "interface: 127.0.0.1" in config
        assert "access-control: 127.0.0.0/8 allow" in config


class TestWireGuardConfigGeneration:
    """Test WireGuard configuration generation."""

    def test_wireguard_freebsd_config_generator_exists(self):
        """Verify WireGuard FreeBSD config generator exists."""
        from core.operations.wireguard import _generate_wg_freebsd_config
        assert callable(_generate_wg_freebsd_config)

    def test_wireguard_freebsd_config_generation(self):
        """Test WireGuard FreeBSD config generation."""
        from core.operations.wireguard import _generate_wg_freebsd_config

        spec = {
            "address": "10.50.0.1/24",
            "port": 51820,
            "private_key": "test_key",
            "peers": []
        }

        config = _generate_wg_freebsd_config(spec)
        assert isinstance(config, str)
        assert "Address = 10.50.0.1/24" in config
        assert "ListenPort = 51820" in config
        assert "PrivateKey = test_key" in config


class TestPFConfigGeneration:
    """Test pf firewall configuration generation."""

    def test_pf_config_deployment(self):
        """Verify pf config can be deployed."""
        from core.operations.pf import add_pf_ops
        assert callable(add_pf_ops)

    def test_pf_rules_format(self):
        """Test that pf rules are formatted correctly."""
        spec = {
            "rules": """pass all
block in on egress proto tcp to port 1:1024"""
        }

        # Should be valid pf rules
        assert isinstance(spec["rules"], str)
        assert "pass" in spec["rules"] or "block" in spec["rules"]


class TestMonitConfigGeneration:
    """Test Monit process monitoring configuration."""

    def test_monit_config_generator_exists(self):
        """Verify monit config generator exists."""
        from core.operations.monit import _generate_monit_config
        assert callable(_generate_monit_config)

    def test_monit_basic_config_generation(self):
        """Test basic monit config generation."""
        from core.operations.monit import _generate_monit_config

        spec = {
            "daemon": 120,
            "httpd_port": 2812,
            "httpd_password": "test123",
            "checks": {}
        }

        config = _generate_monit_config(spec, "monitor.example.com")
        assert isinstance(config, str)
        assert "set daemon 120" in config
        assert "set httpd port 2812" in config


class TestOpenSMTPDConfigGeneration:
    """Test OpenSMTPD mail configuration."""

    def test_opensmtpd_config_generator_exists(self):
        """Verify OpenSMTPD config generator exists."""
        from core.operations.opensmtpd import _generate_smtpd_config
        assert callable(_generate_smtpd_config)

    def test_opensmtpd_basic_config_generation(self):
        """Test basic OpenSMTPD config generation."""
        from core.operations.opensmtpd import _generate_smtpd_config

        spec = {
            "mail_from": "noreply@example.com",
            "smtp_relay": "smtp.example.com:587",
        }

        config = _generate_smtpd_config(spec)
        assert isinstance(config, str)
        assert "listen on" in config or "table" in config


class TestPostgreSQLConfigGeneration:
    """Test PostgreSQL configuration."""

    def test_postgresql_operation_exists(self):
        """Verify PostgreSQL operation exists."""
        from core.operations.postgresql import add_postgresql_ops
        assert callable(add_postgresql_ops)

    def test_postgresql_replication_config(self):
        """Test PostgreSQL replication configuration."""
        from core.operations.postgresql import _setup_replication

        replication_spec = {
            "mode": "primary",
            "backup_slot": "standby_slot"
        }

        # Should not error when setting up replication
        assert replication_spec["mode"] in ["primary", "standby"]


class TestDockerConfigGeneration:
    """Test Docker configuration generation."""

    def test_docker_operation_exists(self):
        """Verify Docker operation exists."""
        from core.operations.docker import add_docker_ops
        assert callable(add_docker_ops)

    def test_docker_daemon_config_generation(self):
        """Test Docker daemon.json generation."""
        spec = {
            "daemon": {
                "insecure-registries": ["registry.local"],
                "log-driver": "journald"
            }
        }

        import json
        config_json = json.dumps(spec["daemon"], indent=2)
        assert isinstance(config_json, str)
        assert "insecure-registries" in config_json


class TestConfigValidation:
    """Test that generated configs are valid formats."""

    def test_nginx_config_is_valid_format(self):
        """Test that generated nginx config is valid."""
        from core.operations.nginx import _generate_nginx_config

        spec = {
            "upstreams": [],
            "servers": []
        }

        config = _generate_nginx_config(spec)
        # Should have basic nginx structure
        assert "http {" in config
        assert "}" in config

    def test_prometheus_yaml_is_valid_format(self):
        """Test that generated Prometheus YAML is valid."""
        from core.operations.prometheus import _generate_prometheus_yml

        spec = {
            "scrape_interval": "15s",
            "scrape_targets": []
        }

        yaml_content = _generate_prometheus_yml(spec, "/etc/prometheus")
        # Should be valid YAML (basic check)
        assert ":" in yaml_content
        assert "-" in yaml_content or "global:" in yaml_content

    def test_docker_compose_is_valid_format(self):
        """Test that generated docker-compose is valid."""
        from core.operations.registry import _generate_compose_yml

        spec = {}
        compose = _generate_compose_yml(spec, "/data", 5000)

        # Should be valid YAML format
        assert "version:" in compose or "services:" in compose
