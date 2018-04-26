#!/usr/bin/python3


import sys
import argparse
import requests
import re
import subprocess
import time
import json
from pprint import pprint as pp


PY3_BIN = '/usr/bin/python3'
PY_BIN = '/usr/bin/python'
IFACE_PY = 'form_iface_configs.py'
ROUTER_PY = 'form_router_bgp_configs.py'
CP_PY = 'copy_file_remote.py'
DEFAULT_IFACE_CONFIGS_DIR = './iface_configs'
DEFAULT_ROUTER_CONFIGS_DIR = './router_configs'
RUN_COMMAND_PY = 'run_command.py'


def create_docker_node(json_topo={}, name=None, image=None, adapters=1):
    # prepare request
    url = 'http://{}:3080/v2/projects/{}/nodes'.format(
        json_topo['url'],
        json_topo['project']['project_id']
    )

    headers = {}
    symbol = ':/symbols/docker_guest.svg'
    if name.startswith('R'):
        symbol = ':/symbols/router.svg'
    payload = json.dumps({
        'name': name,
        'symbol': symbol,
        'node_type': 'docker',
        'compute_id': 'local',
        'properties': {
            'image': image,
            'console_type': 'telnet',
            'adapters': adapters
        }
    })

    # execute request
    res = requests.post(url, data=payload, headers=headers)

    # retrieve (needed) node data
    try:
        json_res = res.json()
        if 'node_id' in json_res:
            json_topo['gns3-nodes'][name] = json_res
            del json_topo['gns3-nodes'][name]['x']
            del json_topo['gns3-nodes'][name]['width']
            del json_topo['gns3-nodes'][name]['name']
            del json_topo['gns3-nodes'][name]['label']
            del json_topo['gns3-nodes'][name]['height']
            del json_topo['gns3-nodes'][name]['y']
            del json_topo['gns3-nodes'][name]['status']
            del json_topo['gns3-nodes'][name]['z']
            del json_topo['gns3-nodes'][name]['symbol']
        else:
            raise
    except:
        print('Request to create GNS3 node {} failed with text:'.format(name))
        pp(res.json())
        sys.exit(1)

    return json_topo


def create_docker_link(json_topo={}, src_hname=None, src_anum=0, dst_hname=None, dst_anum=0):
    # form link name
    name = '{}:{}-{}:{}'.format(src_hname,
                                src_anum,
                                dst_hname,
                                dst_anum)

    # prepare request
    url = 'http://{}:3080/v2/projects/{}/links'.format(
        json_topo['url'],
        json_topo['project']['project_id']
    )

    headers = {}
    payload = json.dumps({
        'nodes': [
            {
                'adapter_number': src_anum,
                'port_number': 0,
                'node_id': json_topo['gns3-nodes'][src_hname]['node_id']
            },
            {
                'adapter_number': dst_anum,
                'port_number': 0,
                'node_id': json_topo['gns3-nodes'][dst_hname]['node_id']
            },
        ]
    })

    # execute request
    res = requests.post(url, data=payload, headers=headers)

    # retrieve (needed) link data
    try:
        json_res = res.json()
        if 'link_id' in json_res:
            json_topo['gns3-links'][name] = json_res
            del json_topo['gns3-links'][name]['capture_file_name']
            del json_topo['gns3-links'][name]['capture_file_path']
            del json_topo['gns3-links'][name]['capturing']
            del json_topo['gns3-links'][name]['suspend']
            del json_topo['gns3-links'][name]['filters']
            for node in json_topo['gns3-links'][name]['nodes']:
                del node['label']
        else:
            raise
    except:
        print('Request to create GNS3 link {} failed with text:'.format(name))
        pp(res.json())
        sys.exit(1)

    return json_topo


def start_node(json_topo, node_name):
    # prepare request
    url = 'http://{}:3080/v2/projects/{}/nodes/{}/start'.format(
        json_topo['url'],
        json_topo['project']['project_id'],
        json_topo['gns3-nodes'][node_name]['node_id']
    )

    headers = {}
    payload = json.dumps({})
    # execute request
    res = requests.post(url, data=payload, headers=headers)


def stop_node(json_topo, node_name):
    # prepare request
    url = 'http://{}:3080/v2/projects/{}/nodes/{}/stop'.format(
        json_topo['url'],
        json_topo['project']['project_id'],
        json_topo['gns3-nodes'][node_name]['node_id']
    )

    headers = {}
    payload = json.dumps({})
    # execute request
    res = requests.post(url, data=payload, headers=headers)


def run_command(json_topo, node_name, command):
    url = 'http://{}:3080/v2/projects/{}/nodes/{}'.format(
        json_topo['url'],
        json_topo['project']['project_id'],
        json_topo['gns3-nodes'][node_name]['node_id']
    )

    headers = {}
    res = requests.get(url, headers=headers)

    if res.json()['status'] == 'stopped':
        start_node(json_topo, node_name)
        time.sleep(2)

    telnet_ip = json_topo['url']
    telnet_port = str(json_topo['gns3-nodes'][node_name]['console'])

    print('\t Running commands on {}'.format(node_name))
    subprocess.call([PY_BIN, RUN_COMMAND_PY, '-ti', telnet_ip, '-tp',
                     telnet_port, '-c', str(command)])

    if res.json()['status'] == 'stopped':
        stop_node(json_topo, node_name)


def main():
    parser = argparse.ArgumentParser(
        description='create a GNS3 multi-domain topology with policies')
    parser.add_argument('-i', '--input', dest='input_topo_file', type=str,
                        help='file with input AS-level topology description', required=True)
    parser.add_argument('-v', '--vm', dest='vm_ip', type=str,
                        help='GNS3 VM IP', default='192.168.163.132')
    args = parser.parse_args()

    with open(args.input_topo_file, 'r') as f:
        json_topo = json.load(f)

    json_topo['url'] = args.vm_ip

    # TODO: validate the json topo file!

    # Create project
    if 'project_id' not in json_topo['project']:
        print('Creating GNS3 project...')
        url = 'http://{}:3080/v2/projects'.format(json_topo['url'])
        payload = json.dumps({
            'name': json_topo['project']['name']
        })
        headers = {}
        res = requests.post(url, data=payload, headers=headers)
        try:
            json_res = res.json()
            if 'project_id' in json_res:
                json_topo['project']['project_id'] = json_res['project_id']
                json_topo['project']['path'] = json_res['path']
                json_topo['project']['filename'] = json_res['filename']
            else:
                raise
        except:
            print('Request to create GNS3 project {} failed with text:'.format(
                json_topo['project']['name']))
            pp(res.json())
            sys.exit(1)

        with open(args.input_topo_file, 'w') as f:
            json.dump(json_topo, f, indent=2)

    print('GNS3 project created!')

    # Create nodes
    print('Creating GNS3 nodes...')
    if 'gns3-nodes' not in json_topo:
        json_topo['gns3-nodes'] = {}

    for node in sorted(json_topo['as-nodes'].keys()):
        node_num = node.split('AS')[1]

        # create host
        as_host_name = 'H{}'.format(node_num)
        print('\t Creating {}...'.format(as_host_name))
        if as_host_name not in json_topo['gns3-nodes']:
            json_topo = create_docker_node(
                json_topo, name=as_host_name, image='gns3/endhost', adapters=1)
            with open(args.input_topo_file, 'w') as f:
                json.dump(json_topo, f, indent=2)
        print('\t {} created!'.format(as_host_name))

        # create router
        as_router_name = 'R{}'.format(node_num)
        print('\t Creating {}...'.format(as_router_name))
        if as_router_name not in json_topo['gns3-nodes']:
            json_topo = create_docker_node(
                json_topo, name=as_router_name, image='ajnouri/quagga_alpine', adapters=5)
            with open(args.input_topo_file, 'w') as f:
                json.dump(json_topo, f, indent=2)
        print('\t {} created!'.format(as_router_name))

        if json_topo['as-nodes'][node]['SDN']:
            # create OVS
            as_ovs_name = 'OVS{}'.format(node_num)
            print('\t Creating {}...'.format(as_ovs_name))
            if as_ovs_name not in json_topo['gns3-nodes']:
                json_topo = create_docker_node(
                    json_topo, name=as_ovs_name, image='gns3/openvswitch', adapters=6)
                with open(args.input_topo_file, 'w') as f:
                    json.dump(json_topo, f, indent=2)
            print('\t {} created!'.format(as_ovs_name))

            commands = [
                'ovs-vsctl set-fail-mode br0 secure',
                'ovs-vsctl set-controller br0 tcp:1.0.0.1:6653'
            ]
            for i in range(6, 16):
                commands.append('ovs-vsctl del-port br0 eth{}'.format(i))
            for i in range(1, 4):
                commands.append('ovs-vsctl del-br br{}'.format(i))
            run_command(json_topo, as_ovs_name, commands)

            # create ONOS
            as_onos_name = 'ONOS{}'.format(node_num)
            print('\t Creating {}...'.format(as_onos_name))
            if as_onos_name not in json_topo['gns3-nodes']:
                json_topo = create_docker_node(
                    json_topo, name=as_onos_name, image='mavromat/onos-artemis', adapters=3)
                with open(args.input_topo_file, 'w') as f:
                    json.dump(json_topo, f, indent=2)
            print('\t {} created!'.format(as_onos_name))

        if json_topo['as-nodes'][node]['EXA']:
            # create ExaBGP Monitor
            as_exa_name = 'EXA{}'.format(node_num)
            print('\t Creating {}...'.format(as_exa_name))
            if as_exa_name not in json_topo['gns3-nodes']:
                json_topo = create_docker_node(
                    json_topo, name=as_exa_name, image='mavromat/exabgp-monitor', adapters=2)
                with open(args.input_topo_file, 'w') as f:
                    json.dump(json_topo, f, indent=2)
            print('\t {} created!'.format(as_exa_name))

    # Create global switch
    global_switch = 'Switch0'
    print('\t Creating {}...'.format(global_switch))
    if global_switch not in json_topo['gns3-nodes']:
        json_topo = create_docker_node(
            json_topo, name=global_switch, image='gns3/openvswitch', adapters=16)
        with open(args.input_topo_file, 'w') as f:
            json.dump(json_topo, f, indent=2)

        run_command(json_topo, global_switch,
                    ['ovs-vsctl set-fail-mode br0 standalone'])
    print('\t {} created!'.format(global_switch))

    print('All GNS3 nodes created!')

    # Create links
    print('Creating GNS3 links...')
    if 'gns3-links' not in json_topo:
        json_topo['gns3-links'] = {}

    # initializing next available adapter counts to
    next_av_adapter = {}
    for node in json_topo['gns3-nodes']:
        next_av_adapter[node] = 0

    # Connecting Devices with OVS switches (internal)
    for node in sorted(json_topo['as-nodes'].keys()):
        node_num = node.split('AS')[1]

        def connect_link_between(json_topo, node1, node2):
            link_name = '{}:{}-{}:{}'.format(node1,
                                             next_av_adapter[node1],
                                             node2,
                                             next_av_adapter[node2])
            print('\t Connecting {}:{} with {}:{}...'.format(node1,
                                                             next_av_adapter[node1],
                                                             node2,
                                                             next_av_adapter[node2]))
            if link_name not in json_topo['gns3-links']:
                json_topo = create_docker_link(json_topo,
                                               src_hname=node1,
                                               src_anum=next_av_adapter[node1],
                                               dst_hname=node2,
                                               dst_anum=next_av_adapter[node2])
                with open(args.input_topo_file, 'w') as f:
                    json.dump(json_topo, f, indent=2)
            print('\t {}:{} with {}:{} connected!'.format(node1,
                                                          next_av_adapter[node1],
                                                          node2,
                                                          next_av_adapter[node2]))
            next_av_adapter[node1] += 1
            next_av_adapter[node2] += 1

        if json_topo['as-nodes'][node]['SDN']:
            as_conn_name = 'OVS{}'.format(node_num)
            next_av_adapter[as_conn_name] = 1

            devices = []
            onos_name = 'ONOS{}'.format(node_num)
            devices.append(onos_name)
            router_name = 'R{}'.format(node_num)
            devices.append(router_name)
            host_name = 'H{}'.format(node_num)
            devices.append(host_name)

            for device in devices:
                connect_link_between(json_topo, as_conn_name, device)

            # Connect ONOS with BGP Speaker
            connect_link_between(json_topo, onos_name, router_name)

            # Connect Monitor with BGP Speaker
            exa_name = 'EXA{}'.format(node_num)
            connect_link_between(json_topo, router_name, exa_name)

            # Connect ONOS and Monitors to a global switch (it will be a tunnel or other prefix in real world)
            connect_link_between(json_topo, onos_name, 'Switch0')
            connect_link_between(json_topo, exa_name, 'Switch0')
        else:
            as_host_name = 'H{}'.format(node_num)
            as_conn_name = 'R{}'.format(node_num)

            connect_link_between(json_topo, as_host_name, as_conn_name)

    # Connecting AS routers with other AS routers (external)
    for link in sorted(json_topo['as-links']):
        (src_as, dst_as) = link.split('-')
        src_as_num = src_as.split('AS')[1]
        dst_as_num = dst_as.split('AS')[1]

        if json_topo['as-nodes'][src_as]['SDN']:
            src_router_name = 'OVS{}'.format(src_as_num)
        else:
            src_router_name = 'R{}'.format(src_as_num)

        if json_topo['as-nodes'][dst_as]['SDN']:
            dst_router_name = 'OVS{}'.format(dst_as_num)
        else:
            dst_router_name = 'R{}'.format(dst_as_num)

        connect_link_between(json_topo, src_router_name, dst_router_name)

    print('All GNS3 links created!')

    print('Configuring the network interfaces of GNS3 nodes...')
    subprocess.call([PY3_BIN, IFACE_PY, '-i',
                     args.input_topo_file, '-o', DEFAULT_IFACE_CONFIGS_DIR])
    for node in json_topo['gns3-nodes']:
        cfg_file = '{}/{}_intf.cfg'.format(DEFAULT_IFACE_CONFIGS_DIR, node)
        dest_file_path = '/opt/gns3/projects/{}/project-files/docker/{}/etc/network/interfaces'.format(
            json_topo['project']['project_id'],
            json_topo['gns3-nodes'][node]['node_id'])
        subprocess.call([PY3_BIN, CP_PY, '-f', cfg_file, '-i',
                         json_topo['url'], '-p', dest_file_path])
    print('All interfaces of all GNS3 nodes configured!')

    print('Configuring the GNS3 BGP routers...')
    subprocess.call([PY3_BIN, ROUTER_PY, '-i',
                     args.input_topo_file, '-o', DEFAULT_ROUTER_CONFIGS_DIR])
    for node in json_topo['gns3-nodes']:
        if re.match('^R\d+$', node):
            zebra_conf_file = '{}/zebra.conf'.format(
                DEFAULT_ROUTER_CONFIGS_DIR)
            dest_file_path = '/opt/gns3/projects/{}/project-files/docker/{}/etc/quagga/zebra.conf'.format(
                json_topo['project']['project_id'],
                json_topo['gns3-nodes'][node]['node_id'])
            subprocess.call([PY3_BIN, CP_PY, '-f', zebra_conf_file,
                             '-i', args.vm_ip, '-p', dest_file_path])

            router_conf_file = '{}/{}_bgpd.conf'.format(
                DEFAULT_ROUTER_CONFIGS_DIR, node)
            dest_file_path = '/opt/gns3/projects/{}/project-files/docker/{}/etc/quagga/bgpd.conf'.format(
                json_topo['project']['project_id'],
                json_topo['gns3-nodes'][node]['node_id'])
            subprocess.call([PY3_BIN, CP_PY, '-f', router_conf_file,
                             '-i', args.vm_ip, '-p', dest_file_path])

            disable_rp_filter_file = '{}/disable_rp_filter'.format(
                DEFAULT_ROUTER_CONFIGS_DIR)
            dest_file_path = '/opt/gns3/projects/{}/project-files/docker/{}/etc/network/if-up.d/disable_rp_filter'.format(
                json_topo['project']['project_id'],
                json_topo['gns3-nodes'][node]['node_id'])
            subprocess.call([PY3_BIN, CP_PY, '-f', disable_rp_filter_file,
                             '-i', args.vm_ip, '-p', dest_file_path])
    print('All GNS3 BGP routers configured!')


if __name__ == '__main__':
    main()
