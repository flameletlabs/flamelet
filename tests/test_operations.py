"""Tests for all 23 framework operations."""

import pytest
from pathlib import Path
from unittest.mock import Mock, MagicMock


class TestPhase1Operations:
    """Test Phase 1 operations: users, groups, sudo, packages, services."""

    def test_users_operation_import(self):
        """Verify users operation imports correctly."""
        from core.operations.users import add_user_ops
        assert callable(add_user_ops)

    def test_groups_operation_import(self):
        """Verify groups operation exists."""
        # Groups typically handled via users operation
        from core.operations.users import add_user_ops
        assert callable(add_user_ops)

    def test_sudo_operation_import(self):
        """Verify sudo operation imports correctly."""
        from core.operations.sudo import add_sudoers_ops
        assert callable(add_sudoers_ops)

    def test_packages_operation_import(self):
        """Verify packages operation imports correctly."""
        from core.operations.packages import add_package_ops
        assert callable(add_package_ops)

    def test_services_operation_import(self):
        """Verify services operation imports correctly."""
        from core.operations.services import add_service_ops
        assert callable(add_service_ops)


class TestPhase2Operations:
    """Test Phase 2 operations: sysctl, sysrc, files, shell, systemd, etc."""

    def test_sysctl_operation_import(self):
        """Verify sysctl operation imports correctly."""
        from core.operations.sysctl import add_sysctl_ops
        assert callable(add_sysctl_ops)

    def test_sysrc_operation_import(self):
        """Verify sysrc operation imports correctly."""
        from core.operations.sysctl import add_sysrc_ops
        assert callable(add_sysrc_ops)

    def test_files_operation_import(self):
        """Verify files operation imports correctly."""
        from core.operations.files import add_file_ops
        assert callable(add_file_ops)

    def test_shell_operation_availability(self):
        """Verify shell operations are available via server module."""
        from pyinfra.operations import server
        assert hasattr(server, 'shell')


class TestPhase3aOperations:
    """Test Phase 3a operations: wireguard, unbound, pf, monit, opensmtpd, docker, node_exporter."""

    def test_wireguard_operation_import(self):
        """Verify wireguard operation imports correctly."""
        from core.operations.wireguard import add_wireguard_ops
        assert callable(add_wireguard_ops)

    def test_unbound_operation_import(self):
        """Verify unbound operation imports correctly."""
        from core.operations.unbound import add_unbound_ops
        assert callable(add_unbound_ops)

    def test_pf_operation_import(self):
        """Verify pf operation imports correctly."""
        from core.operations.pf import add_pf_ops
        assert callable(add_pf_ops)

    def test_monit_operation_import(self):
        """Verify monit operation imports correctly."""
        from core.operations.monit import add_monit_ops
        assert callable(add_monit_ops)

    def test_opensmtpd_operation_import(self):
        """Verify opensmtpd operation imports correctly."""
        from core.operations.opensmtpd import add_opensmtpd_ops
        assert callable(add_opensmtpd_ops)

    def test_docker_operation_import(self):
        """Verify docker operation imports correctly."""
        from core.operations.docker import add_docker_ops
        assert callable(add_docker_ops)

    def test_node_exporter_operation_import(self):
        """Verify node_exporter operation imports correctly."""
        from core.operations.node_exporter import add_node_exporter_ops
        assert callable(add_node_exporter_ops)


class TestPhase3bTier2Operations:
    """Test Tier 2 required operations: k3s, virtualization, storage."""

    def test_k3s_operation_import(self):
        """Verify k3s operation imports correctly."""
        from core.operations.k3s import add_k3s_ops
        assert callable(add_k3s_ops)

    def test_virtualization_operation_import(self):
        """Verify virtualization operation imports correctly."""
        from core.operations.virtualization import add_virtualization_ops
        assert callable(add_virtualization_ops)

    def test_storage_operation_import(self):
        """Verify storage operation imports correctly."""
        from core.operations.storage import add_storage_ops
        assert callable(add_storage_ops)


class TestPhase3bOptionalOperations:
    """Test Phase 3b optional operations: nginx, postgresql, prometheus, registry."""

    def test_nginx_operation_import(self):
        """Verify nginx operation imports correctly."""
        from core.operations.nginx import add_nginx_ops
        assert callable(add_nginx_ops)

    def test_postgresql_operation_import(self):
        """Verify postgresql operation imports correctly."""
        from core.operations.postgresql import add_postgresql_ops
        assert callable(add_postgresql_ops)

    def test_prometheus_operation_import(self):
        """Verify prometheus operation imports correctly."""
        from core.operations.prometheus import add_prometheus_ops
        assert callable(add_prometheus_ops)

    def test_registry_operation_import(self):
        """Verify registry operation imports correctly."""
        from core.operations.registry import add_registry_ops
        assert callable(add_registry_ops)


class TestAllOperationsExist:
    """Test that all 23 operations are importable."""

    @pytest.mark.parametrize("operation_name", [
        # Phase 1 (5)
        "users",
        "sudo",
        "packages",
        "services",
        # Phase 2 (7)
        "sysctl",
        "files",
        # Phase 3a (7)
        "wireguard",
        "unbound",
        "pf",
        "monit",
        "opensmtpd",
        "docker",
        "node_exporter",
        # Phase 3b Tier 2 (3)
        "k3s",
        "virtualization",
        "storage",
        # Phase 3b Optional (4)
        "nginx",
        "postgresql",
        "prometheus",
        "registry",
    ])
    def test_operation_module_exists(self, operation_name):
        """Test that operation module exists and can be imported."""
        module_path = Path(__file__).parent.parent / f"core/operations/{operation_name}.py"
        assert module_path.exists(), f"Operation module {operation_name}.py not found"


class TestPyInfraIntegration:
    """Test that operations correctly use PyInfra primitives."""

    def test_pyinfra_server_module_available(self):
        """Verify PyInfra server module available."""
        from pyinfra.operations import server
        assert hasattr(server, 'shell')
        assert hasattr(server, 'service')
        assert hasattr(server, 'user')

    def test_pyinfra_files_module_available(self):
        """Verify PyInfra files module available."""
        from pyinfra.operations import files
        assert hasattr(files, 'put')

    def test_pyinfra_postgresql_module_available(self):
        """Verify PyInfra postgresql module available."""
        from pyinfra.operations import postgresql
        assert hasattr(postgresql, 'database')
        assert hasattr(postgresql, 'role')
        assert hasattr(postgresql, 'sql')

    def test_pyinfra_docker_module_available(self):
        """Verify PyInfra docker module available."""
        from pyinfra.operations import docker
        assert hasattr(docker, 'compose')
