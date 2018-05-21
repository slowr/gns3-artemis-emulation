#!/usr/bin/python3

import os
import json
import argparse
import re
from collections import defaultdict


def main():
    parser = argparse.ArgumentParser(description='form GSN3 docker node iface configs')
    parser.add_argument('-i', '--input', dest='input_topo_file', type=str, help='file with input GNS3 topology description', required=True)
    parser.add_argument('-o', '--output', dest='output_iface_configs', type=str, help='directory with output iface configs', default='./sample_iface_configs')
    args = parser.parse_args()

    with open(args.input_topo_file, 'r') as f:
        json_topo = json.load(f)

    if not os.path.isdir(args.output_iface_configs):
        os.mkdir(args.output_iface_configs)

    intf_config = {}
    for node in sorted(json_topo['gns3-nodes']):
        intf_config[node] = ''

    for link in sorted(json_topo['gns3-links']):
        r = re.match('^(\S+)(\d+):(\d+)-(\S+)(\d+):(\d+)$', link)
        if r:
            src_node_type, src_node_num = r.group(1), int(r.group(2))
            src_anum = r.group(3)
            dst_node_type, dst_node_num = r.group(4), int(r.group(5))
            dst_anum = r.group(6)

            src_node = '{}{}'.format(src_node_type, src_node_num)
            src_iface = 'eth{}'.format(src_anum)
            dst_node = '{}{}'.format(dst_node_type, dst_node_num)
            dst_iface = 'eth{}'.format(dst_anum)


            tmp_src = '\nauto {}\n'.format(src_iface)
            tmp_src += 'iface {} inet static\n'.format(src_iface)

            tmp_dst = '\nauto {}\n'.format(dst_iface)
            tmp_dst += 'iface {} inet static\n'.format(dst_iface)

            if src_node_type == 'H':
                tmp_src += '\taddress 10.{}.0.100\n'.format(src_node_num)
                tmp_src += '\tnetmask 255.255.254.0\n'
                tmp_src += '\tgateway 10.{}.0.1\n'.format(src_node_num)

                if dst_node_type == 'R':
                    tmp_dst += '\taddress 10.{}.0.1\n'.format(dst_node_num)
                    tmp_dst += '\tnetmask 255.255.254.0\n'

                    intf_config[dst_node] += tmp_dst

                intf_config[src_node] += tmp_src

            elif dst_node_type == 'H':
                tmp_dst += '\taddress 10.{}.0.100\n'.format(dst_node_num)
                tmp_dst += '\tnetmask 255.255.254.0\n'
                tmp_dst += '\tgateway 10.{}.0.1\n'.format(dst_node_num)

                if src_node_type == 'R':
                    tmp_src += '\taddress 10.{}.0.1\n'.format(src_node_num)
                    tmp_src += '\tnetmask 255.255.254.0\n'

                    intf_config[src_node] += tmp_src
                intf_config[dst_node] += tmp_dst

            elif src_node_type == 'R' and dst_node_type == 'R':
                tmp_src += '\taddress 5.{}.{}.'.format(min(src_node_num, dst_node_num), max(src_node_num, dst_node_num))
                tmp_dst += '\taddress 5.{}.{}.'.format(min(src_node_num, dst_node_num), max(src_node_num, dst_node_num))
                if src_node_num < dst_node_num:
                    tmp_src += '1\n'
                    tmp_dst += '2\n'
                else:
                    tmp_src += '2\n'
                    tmp_dst += '1\n'
                tmp_src += '\tnetmask 255.255.255.252\n'
                tmp_dst += '\tnetmask 255.255.255.252\n'

                intf_config[src_node] += tmp_src
                intf_config[dst_node] += tmp_dst

            elif dst_node_type == 'Switch':
                if src_node_type == 'ONOS':
                    tmp_src += '\taddress 100.0.0.{}\n'.format(int(src_node_num) * 2 - 1)
                elif src_node_type == 'EXA':
                    tmp_src += '\taddress 100.0.0.{}\n'.format(int(src_node_num) * 2)
                tmp_src += '\tnetmask 255.255.255.0\n'

                intf_config[src_node] += tmp_src

            elif src_node_type == 'Switch':
                if dst_node_type== 'ONOS':
                    tmp_dst += '\taddress 100.0.0.{}\n'.format(int(dst_node_num) * 2 - 1)
                elif dst_node_type == 'EXA':
                    tmp_dst += '\taddress 100.0.0.{}\n'.format(int(dst_node_num) * 2)
                tmp_dst += '\tnetmask 255.255.255.0\n'

                intf_config[dst_node] += tmp_dst

            elif (src_node_type == 'OVS' and dst_node_type == 'ONOS') or (src_node_type == 'ONOS' and dst_node_type == 'OVS'):
                tmp_dst += '\taddress 1.0.0.'
                tmp_src += '\taddress 1.0.0.'
                if dst_node_type == 'ONOS':
                    tmp_dst += '1\n'
                    tmp_src += '2\n'
                else:
                    tmp_dst += '2\n'
                    tmp_src += '1\n'
                tmp_dst += '\tnetmask 255.255.255.252\n'
                tmp_src += '\tnetmask 255.255.255.252\n'

                intf_config[src_node] += tmp_src
                intf_config[dst_node] += tmp_dst

            elif (src_node_type == 'R' and dst_node_type == 'ONOS') or (src_node_type == 'ONOS' and dst_node_type == 'R'):
                tmp_dst += '\taddress 4.0.0.'
                tmp_src += '\taddress 4.0.0.'
                if dst_node_type == 'ONOS':
                    tmp_dst += '1\n'
                    tmp_src += '2\n'
                else:
                    tmp_dst += '2\n'
                    tmp_src += '1\n'
                tmp_dst += '\tnetmask 255.255.255.252\n'
                tmp_src += '\tnetmask 255.255.255.252\n'

                intf_config[src_node] += tmp_src
                intf_config[dst_node] += tmp_dst

            elif src_node_type == 'R' and dst_node_type == 'OVS':
                if src_node_num == dst_node_num:
                    tmp_src += '\thwaddress ether bb:bb:bb:bb:bb:bb\n'

                tmp_src += '\taddress 5.{}.{}.'.format(min(src_node_num, dst_node_num), max(src_node_num, dst_node_num))

                if src_node_num < dst_node_num:
                    tmp_src += '1\n'
                else:
                    tmp_src += '2\n'

                tmp_src += '\tnetmask 255.255.255.252\n'

                intf_config[src_node] += tmp_src

            elif src_node_type == 'OVS' and dst_node_type == 'R':
                if src_node_num == dst_node_num:
                    tmp_dst += '\thwaddress ether bb:bb:bb:bb:bb:bb\n'
                tmp_dst += '\taddress 5.{}.{}.'.format(min(src_node_num, dst_node_num), max(src_node_num, dst_node_num))

                if src_node_num < dst_node_num:
                    tmp_dst += '2\n'
                else:
                    tmp_dst += '1\n'

                tmp_dst += '\tnetmask 255.255.255.252\n'

                intf_config[dst_node] += tmp_dst

            elif (src_node_type == 'R' and dst_node_type == 'EXA') or (src_node_type == 'EXA' and dst_node_type == 'R'):
                tmp_dst += '\taddress 3.0.0.'
                tmp_src += '\taddress 3.0.0.'

                if src_node_type == 'R':
                    tmp_src += '1\n'
                    tmp_dst += '2\n'
                else:
                    tmp_src += '2\n'
                    tmp_dst += '1\n'

                tmp_src += '\tnetmask 255.255.255.252\n'
                tmp_dst += '\tnetmask 255.255.255.252\n'

                intf_config[src_node] += tmp_src
                intf_config[dst_node] += tmp_dst

    json_topo['intfs'] = defaultdict(dict)
    for node in sorted(intf_config):
        with open('{}/{}_intf.cfg'.format(args.output_iface_configs, node), 'w') as f:
            f.write(intf_config[node])

        def get_nodes(lines):
            iface, address = '', ''
            for line in lines:
                tmp = line.strip()
                if tmp.startswith('iface'):
                    iface = tmp.split(' ')[1]
                elif tmp.startswith('address'):
                    address = tmp.split(' ')[1]
                    yield iface, address

        for iface, address in get_nodes(intf_config[node].splitlines()):
            json_topo['intfs'][node][iface] = address

    with open(args.input_topo_file, 'w') as f:
        json.dump(json_topo, f, indent=2)

if __name__ == '__main__':
    main()
