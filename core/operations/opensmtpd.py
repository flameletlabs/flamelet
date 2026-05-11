"""OpenSMTPD mail relay configuration."""

from io import StringIO

from pyinfra.api.operation import add_op
from pyinfra.operations import files, server
from pyinfra.facts.server import Kernel


def add_opensmtpd_ops(state, hosts, config, target_hosts=None, task="all"):
    """Configure OpenSMTPD mail relay.

    Args:
        state: pyinfra State object
        hosts: Inventory object
        config: dict mapping hostname → OpenSMTPD config
            {
                "example.host": {
                    "mail_from": "noreply@example.com",
                    "smtp_relay": "smtp+tls://username@smtp.example.com:587",
                    "smtp_password": "app-specific-password",
                    "allowed_networks": ["10.0.0.0/24"],
                    "tables": {
                        "aliases": ["root: admin@example.com"],
                        "secrets": ["relay_user relay-password"]
                    }
                }
            }
        target_hosts: list of Host objects (default: all)
        task: "opensmtpd" or "all"
    """
    targets = target_hosts if target_hosts else list(hosts)

    for host in targets:
        if host.name not in config:
            continue

        os_key = host.get_fact(Kernel)
        smtpd_config = config[host.name]

        # Determine config paths
        if os_key == "FreeBSD":
            conf_dir = "/usr/local/etc/mail"
            smtpd_path = f"{conf_dir}/smtpd.conf"
        elif os_key == "OpenBSD":
            conf_dir = "/etc/mail"
            smtpd_path = f"{conf_dir}/smtpd.conf"
        else:  # Linux
            conf_dir = "/etc/opensmtpd"
            smtpd_path = f"{conf_dir}/smtpd.conf"

        # Write smtpd.conf
        content = _generate_smtpd_conf(smtpd_config, conf_dir)
        add_op(
            state,
            files.put,
            name=f"Deploy OpenSMTPD config on {host.name}",
            src=StringIO(content),
            dest=smtpd_path,
            mode="0644",
            user="root",
            group="wheel" if os_key in ("OpenBSD", "FreeBSD") else "root",
            host=host,
        )

        # Write secrets table (high security mode)
        tables = smtpd_config.get("tables", {})
        if "secrets" in tables:
            secrets_path = f"{conf_dir}/secrets"
            secrets_content = "\n".join(tables["secrets"])
            add_op(
                state,
                files.put,
                name=f"Deploy OpenSMTPD secrets on {host.name}",
                src=StringIO(secrets_content),
                dest=secrets_path,
                mode="0640",
                user="root",
                group="_smtpd" if os_key in ("OpenBSD", "FreeBSD") else "mail",
                host=host,
            )

        # Write aliases table
        if "aliases" in tables:
            aliases_path = f"{conf_dir}/aliases"
            aliases_content = "\n".join(tables["aliases"])
            add_op(
                state,
                files.put,
                name=f"Deploy OpenSMTPD aliases on {host.name}",
                src=StringIO(aliases_content),
                dest=aliases_path,
                mode="0644",
                user="root",
                group="wheel" if os_key in ("OpenBSD", "FreeBSD") else "root",
                host=host,
            )

        # Enable service
        if os_key == "FreeBSD":
            add_op(
                state,
                server.shell,
                name=f"Enable OpenSMTPD on {host.name}",
                commands=[
                    "sysrc smtpd_enable=YES",
                    "service smtpd restart || true",
                ],
                host=host,
            )
        elif os_key == "Linux":
            add_op(
                state,
                server.shell,
                name=f"Enable OpenSMTPD on {host.name}",
                commands=[
                    "systemctl enable opensmtpd",
                    "systemctl restart opensmtpd || true",
                ],
                host=host,
            )


def _generate_smtpd_config(config):
    """Generate smtpd.conf config."""
    return _generate_smtpd_conf(config, "/etc/opensmtpd")


def _generate_smtpd_conf(config, conf_dir):
    """Generate smtpd.conf content."""
    lines = []

    # Tables
    lines.append("# Tables")
    lines.append(f"table aliases file:{conf_dir}/aliases")
    if "secrets" in config.get("tables", {}):
        lines.append(f"table secrets file:{conf_dir}/secrets")
    if "allowed_networks" in config:
        lines.append(f"table mynetworks file:{conf_dir}/mynetworks")
    lines.append("")

    # Listeners
    lines.append("# Listeners")
    lines.append("listen on socket")
    lines.append("listen on localhost port 25")
    lines.append("")

    # Actions
    lines.append("# Actions")
    lines.append("action \"local_mail\" mbox alias <aliases>")

    smtp_relay = config.get("smtp_relay", "")
    if smtp_relay:
        lines.append(f"action \"outbound\" relay host {smtp_relay} auth <secrets> mail-from \"{config.get('mail_from')}\"")
    else:
        lines.append(f"action \"outbound\" relay mail-from \"{config.get('mail_from')}\"")
    lines.append("")

    # Rules
    lines.append("# Rules")
    lines.append("match from local for local action \"local_mail\"")
    lines.append("match from local for any action \"outbound\"")

    if "allowed_networks" in config:
        for network in config["allowed_networks"]:
            lines.append(f"match from src {network} for any action \"outbound\"")
    lines.append("")

    return "\n".join(lines)
