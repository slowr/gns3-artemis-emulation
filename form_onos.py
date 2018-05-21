#!/usr/bin/python3

import os
import json
import argparse
import re
from collections import defaultdict
from pprint import pprint as pp
import copy


sample_netcfg = {
    "apps": {
        "org.onosproject.artemis": {
            "artemis": {
                "moas": { },
                "monitors": {
                    "exabgp": [
                    ],
                    "ripe": []
                },
                "prefixes": [
                ]
            }
        },
        "org.onosproject.reactive.routing": {
            "reactiveRouting": {
                "ip4LocalPrefixes": [
                ],
                "ip6LocalPrefixes": [],
                "virtualGatewayMacAddress": "bb:bb:bb:bb:bb:bb"
            }
        },
        "org.onosproject.router": {
            "bgp": {
                "bgpSpeakers" : [
                ]
            }
        }
    },
    "ports": {
    }
}


def extract_neighb_ip_address(this_router_num, neighb_as_num, speaker=False):
    neighb_ip_address = '5.{}.{}.'.format(min(this_router_num, neighb_as_num), max(this_router_num, neighb_as_num))
    if speaker:
        if this_router_num < neighb_as_num:
            neighb_ip_address += '2'
        else:
            neighb_ip_address += '1'
    else:
        if this_router_num > neighb_as_num:
            neighb_ip_address += '2'
        else:
            neighb_ip_address += '1'
    return neighb_ip_address


def main():
    parser = argparse.ArgumentParser(description='form GSN3 quagga router BGP configs')
    parser.add_argument('-i', '--input', dest='input_topo_file', type=str, help='file with input GNS3 topology description', required=True)
    parser.add_argument('-o', '--output', dest='output_router_configs', type=str, help='directory with output router configs', default='./sample_onos_configs')
    args = parser.parse_args()

    with open(args.input_topo_file, 'r') as f:
        json_topo = json.load(f)

    if not os.path.isdir(args.output_router_configs):
        os.mkdir(args.output_router_configs)

    router_neighbs = defaultdict(set)
    for as_link in sorted(json_topo['as-links']):
        r = re.match('^AS(\d+)-AS(\d+)$', as_link)
        if r:
            src_as_num = int(r.group(1))
            dst_as_num = int(r.group(2))
            router_neighbs[src_as_num].add(dst_as_num)
            # reverse link
            if src_as_num not in router_neighbs[dst_as_num]:
                router_neighbs[dst_as_num].add(src_as_num)

    sdn_nodes = []
    for node in json_topo['as-nodes']:
        neigh_num = int(node.split('AS')[1])
        if json_topo['as-nodes']['AS{}'.format(neigh_num)]['SDN']:
            sdn_nodes.append(neigh_num)

    for router in sdn_nodes:
        onos_cfg = copy.deepcopy(sample_netcfg)

        apps = onos_cfg['apps']
        artemis = apps['org.onosproject.artemis']['artemis']

        for node in sdn_nodes:
            if router == node:
                continue
            artemis['monitors']['exabgp'].append('100.0.0.{}:5000'.format(node * 2))

        artemis['prefixes'] = {
                'moas': [],
                'paths': {
                    'origin': '{}'.format(router),
                    'neighbor': []
                },
                'prefix': '100.{}.0.0/23'.format(router)
            }

        neighbors = artemis['prefixes']['paths']['neighbor']

        ipLocalPrefixes = apps['org.onosproject.reactive.routing']['reactiveRouting']['ip4LocalPrefixes']
        ipLocalPrefixes.append({
            'ipPrefix': '10.{}.0.0/23'.format(router),
            'type': 'PUBLIC',
            'gatewayIp': '10.{}.0.1'.format(router)
            })

        peers = []
        for neighbor in router_neighbs[router]:
            ip = extract_neighb_ip_address(router, neighbor, speaker=True)

            ipLocalPrefixes.append({
                'ipPrefix': '{}/30'.format(ip),
                'type': 'PRIVATE',
                'gatewayIp': '{}'.format(ip)
                })

            ip = extract_neighb_ip_address(router, neighbor, speaker=False)
            peers.append(ip)

            neighbors.append({
                'asn': '{}'.format(neighbor),
                'neighbor': []
                })

        apps['org.onosproject.router']['bgp']['bgpSpeakers'] = {
                'name' : 'speaker1',
                'connectPoint' : 'of:0000000000000001/3',
                'peers' : peers
        }

        ports = onos_cfg['ports']
        dpid = 'of:0000000000000001'

        # HOST
        ports['{}/4'.format(dpid)] = {
           "interfaces" : [
                    {
                        'name' : 'sw1-1',
                        'ips'  : [ '10.{}.0.0/23'.format(router) ],
                        'mac'  : 'bb:bb:bb:bb:bb:bb'
                    } 
               ]
           }

        with open('{}/onos{}_netcfg.conf'.format(args.output_router_configs, router), 'w') as f:
            f.write(json.dumps(onos_cfg))


if __name__ == '__main__':
    main()
