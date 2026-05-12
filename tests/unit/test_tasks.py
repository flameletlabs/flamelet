"""Tests for TASK_REGISTRY."""

from core.tasks import TASK_REGISTRY, TaskEntry


class TestTaskRegistry:
    """Test TASK_REGISTRY initialization and structure."""

    def test_registry_initialized(self):
        """TASK_REGISTRY should be a dict."""
        assert isinstance(TASK_REGISTRY, dict)
        assert len(TASK_REGISTRY) > 0

    def test_registry_has_required_tasks(self):
        """Registry should include all required tasks."""
        required_tasks = ["users", "sudo", "packages", "wireguard", "monit"]
        for task in required_tasks:
            assert task in TASK_REGISTRY, f"Missing task: {task}"

    def test_registry_task_entries_valid(self):
        """Each task should have valid TaskEntry objects."""
        for task_name, entries in TASK_REGISTRY.items():
            assert isinstance(entries, list), f"{task_name}: entries must be a list"
            assert len(entries) > 0, f"{task_name}: must have at least one entry"

            for entry in entries:
                assert isinstance(entry, TaskEntry), f"{task_name}: entry must be TaskEntry"
                assert callable(entry.op_func), f"{task_name}: op_func must be callable"
                assert entry.op_type in [
                    "standard",
                    "autossh",
                    "packages",
                    "users",
                    "sudo",
                ], f"{task_name}: invalid op_type {entry.op_type}"

    def test_registry_config_attrs(self):
        """Config attributes should be None or strings."""
        for task_name, entries in TASK_REGISTRY.items():
            for entry in entries:
                assert (
                    entry.config_attr is None or isinstance(entry.config_attr, str)
                ), f"{task_name}: config_attr must be None or str"

    def test_users_and_sudo_have_no_config_attr(self):
        """Users and sudo tasks should have config_attr=None."""
        assert TASK_REGISTRY["users"][0].config_attr is None
        assert TASK_REGISTRY["sudo"][0].config_attr is None

    def test_packages_has_packages_config_attr(self):
        """Packages task should have config_attr='PACKAGES'."""
        assert TASK_REGISTRY["packages"][0].config_attr == "PACKAGES"

    def test_monit_has_monit_config_attr(self):
        """Monit task should have config_attr='MONIT'."""
        assert TASK_REGISTRY["monit"][0].config_attr == "MONIT"

    def test_autossh_has_dual_entries(self):
        """AutoSSH task should have two entries (tunnels + gateway)."""
        assert len(TASK_REGISTRY["autossh"]) == 2
        config_attrs = {e.config_attr for e in TASK_REGISTRY["autossh"]}
        assert "AUTOSSH_TUNNELS" in config_attrs
        assert "AUTOSSH_GATEWAY" in config_attrs

    def test_registry_keys_sorted(self):
        """Registry should be sortable."""
        keys = sorted(TASK_REGISTRY.keys())
        assert len(keys) == len(TASK_REGISTRY)
        assert all(isinstance(k, str) for k in keys)

    def test_operation_functions_importable(self):
        """All operation functions should be importable."""
        for task_name, entries in TASK_REGISTRY.items():
            for entry in entries:
                # If we can call it, it's importable
                assert callable(entry.op_func), f"{task_name}: {entry.op_func} not callable"
