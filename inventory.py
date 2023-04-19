#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Automatic ansible inventory based on containerlab topology file."""

import json
import sys

from ipaddress import ip_network, IPv4Network, IPv6Network
from itertools import chain
from pathlib import Path
from typing import Any, Dict

import yaml


def load_containerlab() -> dict:
    """Load containerlab topology and return as dict."""
    cwd = Path.cwd()
    clab_files = [
        str(f) for f in cwd.iterdir() if str(f).endswith('.clab.yml')
    ]

    # Exit if we find more or less than a single topology file
    if not len(clab_files) == 1:
        print("Error: expected *one* .clab.yml file in CWD but found "
              f"{len(clab_files)}.")
        sys.exit(1)

    try:
        with open(clab_files[0], 'r', encoding='utf-8') as clab_file:
            clab = yaml.safe_load(clab_file.read())
            return clab
    except (IOError) as error:
        print("Error", error)
        sys.exit(1)


def add_lab_nodes(lab: dict):
    """Add lab nodes to INVENTORY."""
    lab_name = lab['name']

    # FIXME: Support multiple "node_vars":
    #        - srlinux
    #        - vmx
    #        - etc.

    # For now we only support Arista EOS vars:
    eos_vars = {
        'ansible_connection': 'ansible.netcommon.network_cli',
        'ansible_network_os': 'arista.eos.eos',
        'ansible_user': 'admin',
        'ansible_password': 'admin',
        'ansible_become': 'yes',
        'ansible_become_method': 'enable',
    }

    lab_nodes = lab['topology']['nodes']
    node_num = 1

    for node, node_details in lab_nodes.items():
        # We blindly assume that node name is prefixed with node type:
        node_type = node.split('-')[0]

        # Add vars based on node 'kind':
        if node_details['kind'] == 'ceos':
            node_vars = eos_vars
        else:
            node_vars = {}

        # Append node_type to 'all' inventory:
        if node_type not in INVENTORY['all']['children']:
            INVENTORY['all']['children'].append(node_type)
            INVENTORY[node_type] = {'hosts': [], 'vars': node_vars}

        INVENTORY[node_type]['hosts'].append(node)

        # Drop netmask from loopback IPs:
        loopback_ipv6 = str(next(ipv6_loop)).split('/', maxsplit=1)[0]
        loopback_ipv4 = str(next(ipv4_loop)).split('/', maxsplit=1)[0]

        # Create clns_net based on padded IPv4 loopback:
        loopback_ipv4_zero_padded = ("".join(
            octet.rjust(3, '0') for octet in loopback_ipv4.split('.')))
        clns_net = (f"49.0001.{loopback_ipv4_zero_padded[0:4]}."
                    f"{loopback_ipv4_zero_padded[4:8]}."
                    f"{loopback_ipv4_zero_padded[8:]}.00")

        INVENTORY['_meta']['hostvars'][node] = {
            'ansible_host': f'clab-{lab_name}-{node}',
            'vars': {
                'loopback_ipv6': loopback_ipv6,
                'loopback_ipv4': loopback_ipv4,
                'clns_net': clns_net,
                'interfaces': {}
            }
        }
        node_num += 1


def add_lab_links(lab: dict):
    """Add lab links to INVENTORY."""
    lab_links = lab['topology']['links']

    for link in lab_links:

        # Allocate IPv4:
        ipv4_pfx = next(ipv4_link)
        assert isinstance(ipv4_pfx, IPv4Network)
        ipv4_pfx_len = ipv4_pfx.prefixlen
        ipv4_pfx_ips = list(ipv4_pfx.hosts())

        # Allocate IPv6:
        ipv6_pfx = next(ipv6_link)
        assert isinstance(ipv6_pfx, IPv6Network)
        ipv6_pfx_len = ipv6_pfx.prefixlen
        ipv6_pfx_ips = list(ipv6_pfx.hosts())

        for endpoint in link['endpoints']:
            node, intf = endpoint.split(':')

            # Find neighbor name:
            _endpoints = [*link['endpoints']]
            _endpoints.pop(_endpoints.index(endpoint))
            neighbor = _endpoints[0].split(':')[0]

            intf_conf = {
                'ipv4': f"{ipv4_pfx_ips.pop()}/{ipv4_pfx_len}",
                'ipv6': f"{ipv6_pfx_ips.pop()}/{ipv6_pfx_len}",
                'neighbor': f"{neighbor}"
            }
            # TODO: Clean-up and commit
            # Add IPv4 and IPv6 neighbor IPs
            intf_conf['ipv4_neighbor'] = ([
                str(host) for host in IPv4Network(intf_conf['ipv4'],
                                                  strict=False).hosts()
                if str(host) != intf_conf['ipv4'].split('/')[0]
            ][0])
            intf_conf['ipv6_neighbor'] = ([
                str(host) for host in IPv6Network(intf_conf['ipv6'],
                                                  strict=False).hosts()
                if str(host) != intf_conf['ipv6'].split('/')[0]
            ][0])

            INVENTORY['_meta']['hostvars'][node]['vars']['interfaces'].update(
                {intf: intf_conf})


def main():
    """Automatic ansible inventory based on containerlab topology file."""
    lab = load_containerlab()
    add_lab_nodes(lab)
    add_lab_links(lab)
    print(json.dumps(INVENTORY, indent=4))


# Create ipv4_loop and ipv4_link pools of RFC5737 address blocks:
ipv4_nets = ["192.0.2.0/24", "198.51.100.0/24", "203.0.113.0/24"]
ipv4_loop = ip_network(ipv4_nets.pop(0)).subnets(new_prefix=32)
ipv4_link = chain(
    *[ip_network(ipv4_net).subnets(new_prefix=31) for ipv4_net in ipv4_nets])

# Create ipv6_loop and ipv6_link pools of RFC3849 addresses:
ipv6_link = ip_network('2001:db8::/33').subnets(new_prefix=127)
ipv6_loop = ip_network('2001:db8:8000::/33').subnets(new_prefix=128)

INVENTORY: Dict[str, Any] = {
    'all': {
        'children': []
    },
    '_meta': {
        'hostvars': {}
    }
}

if __name__ == '__main__':
    main()
