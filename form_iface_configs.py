#!/usr/bin/python3

import os
import ujson
import argparse
import re


def main():
    parser = argparse.ArgumentParser(description='form GSN3 docker node iface configs')
    parser.add_argument('-i', '--input', dest='input_topo_file', type=str, help='file with input GNS3 topology description', required=True)
    parser.add_argument('-o', '--output', dest='output_iface_configs', type=str, help='directory with output iface configs', default='./sample_iface_configs')
    args = parser.parse_args()

    with open(args.input_topo_file, 'r') as f:
        json_topo = ujson.load(f)

    if not os.path.isdir(args.output_iface_configs):
        os.mkdir(args.output_iface_configs)

    intf_config = {}
    for node in sorted(json_topo['gns3-nodes']):
        intf_config[node] = ''

    for link in sorted(json_topo['gns3-links']):
        r = re.match('^(\S+)(\d+):(\d+)-(\S+)(\d+):(\d+)$', link)
        if r:
            src_node_type = r.group(1)
            src_node_num = int(r.group(2))
            src_node = '{}{}'.format(src_node_type, src_node_num)
            src_anum = r.group(3)
            src_iface = 'eth{}'.format(src_anum)
            dst_node_type = r.group(4)
            dst_node_num = int(r.group(5))
            dst_node = '{}{}'.format(dst_node_type, dst_node_num)
            dst_anum = r.group(6)
            dst_iface = 'eth{}'.format(dst_anum)

            # set src node
            intf_config[src_node] += '\nauto {}\n'.format(src_iface)
            intf_config[src_node] += 'iface {} inet static\n'.format(src_iface)
            if src_node_type == 'H':
                intf_config[src_node] += '\taddress 10.{}.0.100\n'.format(src_node_num)
                intf_config[src_node] += '\tnetmask 255.255.255.0\n'
                intf_config[src_node] += '\tgateway 10.{}.0.1\n'.format(src_node_num)
            elif src_node_type == 'R' and dst_node_type == 'H':
                intf_config[src_node] += '\taddress 10.{}.0.1\n'.format(src_node_num)
                intf_config[src_node] += '\tnetmask 255.255.255.0\n'
            elif src_node_type == 'R' and dst_node_type == 'R':
                intf_config[src_node] += '\taddress 10.{}.{}.'.format(min(src_node_num, dst_node_num), max(src_node_num, dst_node_num))
                if src_node_num < dst_node_num:
                    intf_config[src_node] += '1\n'
                else:
                    intf_config[src_node] += '2\n'
                intf_config[src_node] += '\tnetmask 255.255.255.252\n'

            # set dst node
            intf_config[dst_node] += '\nauto {}\n'.format(dst_iface)
            intf_config[dst_node] += 'iface {} inet static\n'.format(dst_iface)
            if dst_node_type == 'H':
                intf_config[dst_node] += '\taddress 10.{}.0.100\n'.format(dst_node_num)
                intf_config[dst_node] += '\tnetmask 255.255.255.0\n'
                intf_config[dst_node] += '\tgateway 10.{}.0.1\n'.format(dst_node_num)
            elif dst_node_type == 'R' and src_node_type == 'H':
                intf_config[dst_node] += '\taddress 10.{}.0.1\n'.format(dst_node_num)
                intf_config[dst_node] += '\tnetmask 255.255.255.0\n'
            elif dst_node_type == 'R' and src_node_type == 'R':
                intf_config[dst_node] += '\taddress 10.{}.{}.'.format(min(src_node_num, dst_node_num), max(src_node_num, dst_node_num))
                if src_node_num > dst_node_num:
                    intf_config[dst_node] += '1\n'
                else:
                    intf_config[dst_node] += '2\n'
                intf_config[dst_node] += '\tnetmask 255.255.255.252\n'

    for node in sorted(intf_config):
        with open('{}/{}_intf.cfg'.format(args.output_iface_configs, node), 'w') as f:
            f.write(intf_config[node])


if __name__ == '__main__':
    main()
