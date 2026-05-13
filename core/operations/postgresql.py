"""PostgreSQL database operations leveraging pyinfra built-ins."""

from io import StringIO

from pyinfra.api.operation import add_op
from pyinfra.facts.server import Kernel
from pyinfra.operations import files, postgresql, server


def add_postgresql_ops(state, hosts, config, target_hosts=None, task="all"):
    """Deploy PostgreSQL server with databases, users, replication setup.

    Args:
        state: pyinfra State object
        hosts: Inventory object
        config: dict mapping hostname → {
            "version": "14",
            "databases": [
                {"name": "myapp", "owner": "appuser"}
            ],
            "users": [
                {"name": "appuser", "password": "...", "can_create_db": True}
            ],
            "replication": {
                "mode": "primary" | "standby",
                "primary_host": "primary.example.com",
                "backup_slot": "standby_slot",
            },
            "extensions": ["uuid-ossp", "pg_stat_statements"],
        }
        target_hosts: list of Host objects to deploy to (default: all)
        task: "postgresql" or "all" (for compatibility)
    """
    targets = target_hosts if target_hosts else list(hosts)

    for host in targets:
        if host.name not in config:
            continue

        spec = config[host.name]
        os_key = host.get_fact(Kernel)

        # Install PostgreSQL
        version = spec.get("version", "14")
        if os_key == "FreeBSD":
            pkg_name = f"postgresql{version}-server"
            data_dir = f"/var/db/postgres/data{version}"
        elif os_key == "OpenBSD":
            pkg_name = f"postgresql-server-{version}"
            data_dir = "/var/postgresql/data"
        else:  # Linux
            pkg_name = f"postgresql-{version}"
            data_dir = "/var/lib/postgresql/14/main"

        # Install PostgreSQL
        add_op(
            state,
            server.shell,
            name=f"Install PostgreSQL {version} on {host.name}",
            commands=[f"which initdb || {_pkg_install_cmd(os_key, pkg_name)}"],
            host=host,
        )

        # Initialize database cluster if not exists
        add_op(
            state,
            server.shell,
            name=f"Initialize PostgreSQL data directory on {host.name}",
            commands=[
                f"test -d {data_dir} || pg_ctl init -D {data_dir}",
                f"chown -R postgres:postgres {data_dir}",
                f"chmod 700 {data_dir}",
            ],
            host=host,
        )

        # Start PostgreSQL
        add_op(
            state,
            server.service,
            name="postgresql",
            state="started",
            enabled=True,
            host=host,
        )

        # Create databases using pyinfra built-in
        for db in spec.get("databases", []):
            add_op(
                state,
                postgresql.database,
                name=f"Create database {db['name']} on {host.name}",
                database=db["name"],
                owner=db.get("owner", "postgres"),
                state="present",
                host=host,
            )

        # Create roles/users using pyinfra built-in
        for user in spec.get("users", []):
            add_op(
                state,
                postgresql.role,
                name=f"Create PostgreSQL user {user['name']} on {host.name}",
                role=user["name"],
                password=user.get("password"),
                state="present",
                superuser=user.get("superuser", False),
                create_db=user.get("can_create_db", False),
                create_role=user.get("can_create_role", False),
                login=user.get("can_login", True),
                host=host,
            )

        # Create extensions
        for extension in spec.get("extensions", []):
            for db in spec.get("databases", []):
                add_op(
                    state,
                    postgresql.sql,
                    name=f"Create extension {extension} in {db['name']} on {host.name}",
                    sql=f"CREATE EXTENSION IF NOT EXISTS {extension};",
                    database=db["name"],
                    host=host,
                )

        # Setup replication if configured
        replication = spec.get("replication")
        if replication:
            _setup_replication(state, host, replication, data_dir, os_key)


def _setup_replication(state, host, replication, data_dir, os_key):
    """Configure streaming replication or standby mode."""
    mode = replication.get("mode", "primary")

    if mode == "primary":
        # Configure primary for streaming replication
        postgres_conf = f"{data_dir}/postgresql.conf"

        add_op(
            state,
            server.shell,
            name=f"Configure PostgreSQL replication on {host.name}",
            commands=[
                f"echo 'wal_level = replica' >> {postgres_conf}",
                f"echo 'max_wal_senders = 10' >> {postgres_conf}",
                f"echo 'wal_keep_segments = 64' >> {postgres_conf}",
                f"echo 'hot_standby = on' >> {postgres_conf}",
            ],
            host=host,
        )

        # Create backup slot if specified
        backup_slot = replication.get("backup_slot")
        if backup_slot:
            add_op(
                state,
                postgresql.sql,
                name=f"Create replication slot {backup_slot} on {host.name}",
                sql=f"SELECT * FROM pg_create_physical_replication_slot('{backup_slot}', true);",
                database="postgres",
                host=host,
            )

    elif mode == "standby":
        # Configure standby for replication
        primary_host = replication.get("primary_host")
        backup_slot = replication.get("backup_slot")

        recovery_conf_content = f"""# Generated by Flamelet - Standby Recovery Configuration
standby_mode = 'on'
primary_conninfo = 'host={primary_host} user=replication password=replication'
restore_command = 'cp {data_dir}/pg_wal/%f %p || exit 1'
recovery_target_timeline = 'latest'
"""
        recovery_conf_path = f"{data_dir}/recovery.conf"

        add_op(
            state,
            files.put,
            name=f"Deploy recovery.conf on {host.name}",
            src=StringIO(recovery_conf_content),
            dest=recovery_conf_path,
            user="postgres",
            group="postgres",
            mode="0600",
            host=host,
        )

        # Take base backup from primary
        if backup_slot:
            add_op(
                state,
                server.shell,
                name=f"Take base backup from {primary_host} on {host.name}",
                commands=[
                    f"pg_basebackup -h {primary_host} -U replication -D {data_dir} "
                    f"-P -v --wal-method=stream --slot={backup_slot}",
                    f"chown -R postgres:postgres {data_dir}",
                    f"chmod 700 {data_dir}",
                ],
                host=host,
            )


def _pkg_install_cmd(os_key, pkg_name):
    """Return OS-specific package install command."""
    if os_key == "FreeBSD":
        return f"pkg install -y {pkg_name}"
    elif os_key == "OpenBSD":
        return f"pkg_add {pkg_name}"
    else:  # Linux
        return f"apt-get update && apt-get install -y {pkg_name}"
