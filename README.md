# clab-ansible-inventory

Automatic Ansible inventory generator for Containerlab topologies. Automates IP address allocation, CLNS addressing, and interface variable generation for rapid lab deployment.

## Requirements

- Python 3
- PyYAML

## Usage

Expects exactly one `.clab.yml` file in the current working directory.

**View inventory:**
```bash
./inventory.py
```

**Use with Ansible:**
```bash
ansible-playbook -i ./inventory.py playbook.yml
```

**Node naming:** Use `<type>-<identifier>` format (e.g., `leaf-1`, `spine-2`). Type is extracted from the first hyphen for inventory grouping.

## What It Generates

- **IPv4/IPv6 loopbacks**: Sequential addresses from RFC test ranges (192.0.2.0/24, 2001:db8:8000::/33)
- **Point-to-point links**: /31 IPv4 and /127 IPv6 subnets
- **CLNS NET addresses**: Derived from IPv4 loopbacks for IS-IS
- **Interface variables**: Each interface includes local IPs, neighbor name, and neighbor IPs
- **Ansible connection settings**: Pre-configured for Arista cEOS (network_cli, credentials)

## Platform Support

The addressing and variable generation works for any platform. Ansible connection settings are currently pre-configured for **Arista cEOS** only. To add connection settings for other platforms, edit `add_lab_nodes()` to map Containerlab `kind` values to appropriate Ansible connection variables.