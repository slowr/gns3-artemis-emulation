#!/usr/bin/python3


import sys
import ujson
import argparse
import requests
import re
import copy
import gns3_topo_gen


def deactivate_link(json_topo, link_name):
    # prepare request
    url = 'http://localhost:3080/v2/projects/{}/links/{}'.format(json_topo['project']['project_id'],
                                                                 json_topo['gns3-links'][link_name]['link_id'])
    headers = {}
    payload = ''

    # execute request
    res = requests.delete(url, data=payload, headers=headers)

    # update json info
    del json_topo['gns3-links'][link_name]['link_id']

    return json_topo


def activate_link(json_topo, link_name):
    match = re.match('(\S+\d+):(\d+)-(\S+\d)+:(\d+)', link_name)
    link_src_node = match.group(1)
    link_src_adapter = int(match.group(2))
    link_dst_node = match.group(3)
    link_dst_adapter = int(match.group(4))

    json_topo = gns3_topo_gen.create_docker_link(json_topo,
                                                 src_hname=link_src_node,
                                                 src_anum=link_src_adapter,
                                                 dst_hname=link_dst_node,
                                                 dst_anum=link_dst_adapter)

    return json_topo


def find_link(json_topo, src_node, dst_node):
    found_link = None
    for link in json_topo['gns3-links']:
        match = re.match('(\S+\d+):\d+-(\S+\d)+:\d+', link)
        link_src = str(match.group(1))
        link_dst = str(match.group(2))
        if (link_src, link_dst) == (src_node, dst_node) or (link_dst, link_src) == (src_node, dst_node):
            found_link = link
            break

    return found_link


def main():
    parser = argparse.ArgumentParser(description='form GSN3 docker node iface configs')
    parser.add_argument('-i', '--input', dest='input_topo_file', type=str, help='file with input GNS3 topology description', required=True)
    parser.add_argument('-s', '--src_node', dest='src_node', type=str, help='source GNS3 node of link', required=True)
    parser.add_argument('-d', '--dst_node', dest='dst_node', type=str, help='destination GNS3 node of link', required=True)
    parser.add_argument('-a', '--activate', dest='activate', help='activate link (default=deactivate)', action='store_true')
    args = parser.parse_args()

    with open(args.input_topo_file, 'r') as f:
        json_topo = ujson.load(f)

    if args.src_node not in json_topo['gns3-nodes']:
        print('Source node '{}' is not a valid gns3 node!'.format(args.src_node))
        sys.exit(1)

    if args.dst_node not in json_topo['gns3-nodes']:
        print('Dest node '{}' is not a valid gns3 node!'.format(args.dst_node))
        sys.exit(1)

    link_name = find_link(json_topo, args.src_node, args.dst_node)
    if link_name is not None:
        if not args.activate:

            if 'link_id' not in json_topo['gns3-links'][link_name]:
                print('Link '{}' is already deactivated, leaving down'.format(link_name))
                sys.exit(1)

            json_topo = deactivate_link(json_topo, link_name)
            print('Deactivated link '{}''.format(link_name))
        else:

            if 'link_id' in json_topo['gns3-links'][link_name]:
                print('Link '{}' is already activated, leaving up'.format(link_name))
                sys.exit(1)

            json_topo = activate_link(json_topo, link_name)
            print('Activated link '{}''.format(link_name))

        with open(args.input_topo_file, 'w') as f:
            ujson.dump(json_topo, f, indent=2)
    else:
        print('Could not find link to control!')


if __name__ == '__main__':
    main()
