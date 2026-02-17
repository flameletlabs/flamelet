# Examples

Tenant examples are available in separate GitHub repositories.

## example-local

**Repository:** [flameletlabs/example-local](https://github.com/flameletlabs/example-local)

Provision the machine where flamelet is running on using a local connection.
This is the simplest example and the best place to start. It includes:

- A minimal `config.sh` with commented explanations
- A localhost-only inventory
- A self-contained playbook (no external roles or collections needed)

```bash
git clone https://github.com/flameletlabs/example-local.git \
  ~/.flamelet/tenant/flamelet-example-local
flamelet -t example-local installansible
flamelet -t example-local -l ansible
```

## example-remote

**Repository:** [flameletlabs/example-remote](https://github.com/flameletlabs/example-remote) *(coming soon)*

Provision remote machines via SSH using a dedicated controller. This example demonstrates:

- SSH controller configuration
- Multi-host inventory
- Galaxy roles and collections
- Tag-based selective provisioning
