#!/usr/bin/python3


import sys
import argparse
import requests
import ujson
import re
import subprocess
import time
from pprint import pprint as pp


PY3_BIN = '/usr/bin/python3'
IFACE_PY = 'form_iface_configs.py'
ROUTER_PY = 'form_router_bgp_configs.py'
CP_PY = 'copy_file_remote.py'
DEFAULT_IFACE_CONFIGS_DIR = './iface_configs'
DEFAULT_ROUTER_CONFIGS_DIR = './router_configs'


def create_docker_node(json_topo={}, name=None, image=None, adapters=1):

    # prepare request
    url = 'http://192.168.163.132:3080/v2/projects/{}/nodes'.format(json_topo['project']['project_id'])
    headers = {}
    symbol = ':/symbols/docker_guest.svg'
    if name.startswith('R'):
        symbol = ':/symbols/router.svg'
    payload = ujson.dumps({
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
        json_res = ujson.loads(res.text)
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
        pp(res.text)
        sys.exit(1)

    return json_topo


def create_docker_link(json_topo={}, src_hname=None, src_anum=0, dst_hname=None, dst_anum=0):

    # form link name
    name = '{}:{}-{}:{}'.format(src_hname,
                                src_anum,
                                dst_hname,
                                dst_anum)

    # prepare request
    url = 'http://192.168.163.132:3080/v2/projects/{}/links'.format(json_topo['project']['project_id'])
    headers = {}
    payload = ujson.dumps({
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
        json_res = ujson.loads(res.text)
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
        pp(res.text)
        sys.exit(1)

    return json_topo


def start_node(json_topo, node_name):

    # prepare request
    url = 'http://192.168.163.132:3080/v2/projects/{}/nodes/{}/start'.format(json_topo['project']['project_id'],
                                                                       json_topo['gns3-nodes'][node_name]['node_id'])
    headers = {}
    payload = ujson.dumps({})

    # execute request
    res = requests.post(url, data=payload, headers=headers)

    return


def stop_node(json_topo, node_name):

    # prepare request
    url = 'http://192.168.163.132:3080/v2/projects/{}/nodes/{}/stop'.format(json_topo['project']['project_id'],
                                                                      json_topo['gns3-nodes'][node_name]['node_id'])
    headers = {}
    payload = ujson.dumps({})

    # execute request
    res = requests.post(url, data=payload, headers=headers)

    return


def main():
    parser = argparse.ArgumentParser(description='create a GNS3 multi-domain topology with policies')
    parser.add_argument('-i', '--input', dest='input_topo_file', type=str, help='file with input AS-level topology description', required=True)
    parser.add_argument('-v', '--vm', dest='vm_ip', type=str, help='GNS3 VM IP', default='192.168.163.132')
    args = parser.parse_args()

    with open(args.input_topo_file, 'r') as f:
        json_topo = ujson.load(f)

    # TODO: validate the json topo file!

    # Create project
    if 'project_id' not in json_topo['project']:
        print('Creating GNS3 project...')
        url = 'http://192.168.163.132:3080/v2/projects'
        payload = ujson.dumps({
            'name': json_topo['project']['name']
        })
        headers = {}
        res = requests.post(url, data=payload, headers=headers)
        try:
            json_res = ujson.loads(res.text)
            if 'project_id' in json_res:
                json_topo['project']['project_id'] = json_res['project_id']
                json_topo['project']['path'] = json_res['path']
                json_topo['project']['filename'] = json_res['filename']
            else:
                raise
        except:
            print('Request to create GNS3 project {} failed with text:'.format(json_topo['project']['name']))
            pp(res.text)
            sys.exit(1)

        with open(args.input_topo_file, 'w') as f:
            ujson.dump(json_topo, f, indent=2)

    print('GNS3 project created!')

    # Create nodes
    print('Creating GNS3 nodes...')
    if 'gns3-nodes' not in json_topo:
        json_topo['gns3-nodes'] = {}

    for node in sorted(json_topo['as-nodes']):
        node_num = node.split('AS')[1]

        # create host
        as_host_name = 'H{}'.format(node_num)
        print('\t Creating {}...'.format(as_host_name))
        if as_host_name not in json_topo['gns3-nodes']:
            json_topo = create_docker_node(json_topo, name=as_host_name, image='gns3/endhost', adapters=1)
            with open(args.input_topo_file, 'w') as f:
                ujson.dump(json_topo, f, indent=2)
        print('\t {} created!'.format(as_host_name))

        # create router
        as_router_name = 'R{}'.format(node_num)
        print('\t Creating {}...'.format(as_router_name))
        if as_router_name not in json_topo['gns3-nodes']:
            json_topo = create_docker_node(json_topo, name=as_router_name, image='ajnouri/quagga_alpine', adapters=5)
            with open(args.input_topo_file, 'w') as f:
                ujson.dump(json_topo, f, indent=2)
        print('\t {} created!'.format(as_router_name))

    print('All GNS3 nodes created!')

    # Create links
    print('Creating GNS3 links...')
    if 'gns3-links' not in json_topo:
        json_topo['gns3-links'] = {}

    # initializing next available adapter counts to
    next_av_adapter = {}
    for node in json_topo['gns3-nodes']:
        next_av_adapter[node] = 0

    # Connecting AS hosts with AS routers (internal)
    for node in sorted(json_topo['as-nodes']):
        node_num = node.split('AS')[1]
        as_host_name = 'H{}'.format(node_num)
        as_router_name = 'R{}'.format(node_num)
        link_name = '{}:{}-{}:{}'.format(as_host_name,
                                         next_av_adapter[as_host_name],
                                         as_router_name,
                                         next_av_adapter[as_router_name])
        print('\t Connecting {}:{} with {}:{}...'.format(as_host_name,
                                                      next_av_adapter[as_host_name],
                                                      as_router_name,
                                                      next_av_adapter[as_router_name]))
        if link_name not in json_topo['gns3-links']:
            json_topo = create_docker_link(json_topo,
                                           src_hname=as_host_name,
                                           src_anum=next_av_adapter[as_host_name],
                                           dst_hname=as_router_name,
                                           dst_anum=next_av_adapter[as_router_name])
            with open(args.input_topo_file, 'w') as f:
                ujson.dump(json_topo, f, indent=2)
        print('\t {}:{} with {}:{} connected!'.format(as_host_name,
                                                      next_av_adapter[as_host_name],
                                                      as_router_name,
                                                      next_av_adapter[as_router_name]))
        next_av_adapter[as_host_name] += 1
        next_av_adapter[as_router_name] += 1

    # Connecting AS routers with other AS routers (external)
    for link in sorted(json_topo['as-links']):
        (src_as, dst_as) = link.split('-')
        src_as_num = src_as.split('AS')[1]
        dst_as_num = dst_as.split('AS')[1]
        src_router_name = 'R{}'.format(src_as_num)
        dst_router_name = 'R{}'.format(dst_as_num)
        link_name = '{}:{}-{}:{}'.format(src_router_name,
                                         next_av_adapter[src_router_name],
                                         dst_router_name,
                                         next_av_adapter[dst_router_name])
        print('\t Connecting {}:{} with {}:{}...'.format(src_router_name,
                                                         next_av_adapter[src_router_name],
                                                         dst_router_name,
                                                         next_av_adapter[dst_router_name]))
        if link_name not in json_topo['gns3-links']:
            json_topo = create_docker_link(json_topo,
                                           src_hname=src_router_name,
                                           src_anum=next_av_adapter[src_router_name],
                                           dst_hname=dst_router_name,
                                           dst_anum=next_av_adapter[dst_router_name])
            with open(args.input_topo_file, 'w') as f:
                ujson.dump(json_topo, f, indent=2)
        print('\t {}:{} with {}:{} connected!'.format(src_router_name,
                                                      next_av_adapter[src_router_name],
                                                      dst_router_name,
                                                      next_av_adapter[dst_router_name]))
        next_av_adapter[src_router_name] += 1
        next_av_adapter[dst_router_name] += 1

    print('All GNS3 links created!')

    print('Waiting for ~30 seconds for a setup reboot')
    for node in sorted(json_topo['gns3-nodes']):
        start_node(json_topo, node_name=node)
    time.sleep(10)
    for node in sorted(json_topo['gns3-nodes']):
        stop_node(json_topo, node_name=node)
    time.sleep(10)

    print('Configuring the network interfaces of GNS3 nodes...')
    subprocess.call([PY3_BIN, IFACE_PY, '-i', args.input_topo_file, '-o', DEFAULT_IFACE_CONFIGS_DIR])
    for node in json_topo['gns3-nodes']:
        cfg_file = '{}/{}_intf.cfg'.format(DEFAULT_IFACE_CONFIGS_DIR, node)
        dest_file_path = '/opt/gns3/projects/{}/project-files/docker/{}/etc/network/interfaces'.format(
            json_topo['project']['project_id'],
            json_topo['gns3-nodes'][node]['node_id'])
        subprocess.call([PY3_BIN, CP_PY, '-f', cfg_file, '-i', args.vm_ip, '-p', dest_file_path])
    time.sleep(5)
    print('All interfaces of all GNS3 nodes configured!')

    print('Configuring the GNS3 BGP routers...')
    subprocess.call([PY3_BIN, ROUTER_PY, '-i', args.input_topo_file, '-o', DEFAULT_ROUTER_CONFIGS_DIR])
    for node in json_topo['gns3-nodes']:
        if re.match('^R\d+$', node):
            zebra_conf_file = '{}/zebra.conf'.format(DEFAULT_ROUTER_CONFIGS_DIR)
            dest_file_path = '/opt/gns3/projects/{}/project-files/docker/{}/etc/quagga/zebra.conf'.format(
                json_topo['project']['project_id'],
                json_topo['gns3-nodes'][node]['node_id'])
            subprocess.call([PY3_BIN, CP_PY, '-f', zebra_conf_file, '-i', args.vm_ip, '-p', dest_file_path])

            router_conf_file = '{}/{}_bgpd.conf'.format(DEFAULT_ROUTER_CONFIGS_DIR, node)
            dest_file_path = '/opt/gns3/projects/{}/project-files/docker/{}/etc/quagga/bgpd.conf'.format(
                json_topo['project']['project_id'],
                json_topo['gns3-nodes'][node]['node_id'])
            subprocess.call([PY3_BIN, CP_PY, '-f', router_conf_file, '-i', args.vm_ip, '-p', dest_file_path])

            disable_rp_filter_file = '{}/disable_rp_filter'.format(DEFAULT_ROUTER_CONFIGS_DIR)
            dest_file_path = '/opt/gns3/projects/{}/project-files/docker/{}/etc/network/if-up.d/disable_rp_filter'.format(
                json_topo['project']['project_id'],
                json_topo['gns3-nodes'][node]['node_id'])
            subprocess.call([PY3_BIN, CP_PY, '-f', disable_rp_filter_file, '-i', args.vm_ip, '-p', dest_file_path])
    time.sleep(5)
    print('All GNS3 BGP routers configured!')

    # print('Starting all GNS3 nodes')
    # for node in sorted(json_topo['gns3-nodes']):
    #     start_node(json_topo, node_name=node)

    # input('Press any key to stop all GNS3 nodes...')

    # print('Stopping all GNS3 nodes')
    # for node in sorted(json_topo['gns3-nodes']):
    #     stop_node(json_topo, node_name=node)


if __name__ == '__main__':
    main()



