#!/usr/bin/python3


import sys
import os
import ujson
import re
import argparse
import subprocess
import time
from pprint import pprint as pp


PY3_BIN = '/usr/bin/python3'
PY_BIN = '/usr/bin/python'
CONTROL_LINK_PY = 'control_gns3_link.py'
GET_AS_TRACE_PY = 'traceroute_parsing/get_telnet_AS_traceroute.py'


def extract_as_link_routers(json_topo, src_as, dst_as):
    src_match = re.match('AS(\d+)', src_as)
    src_router = 'R{}'.format(src_match.group(1))
    dst_match = re.match('AS(\d+)', dst_as)
    dst_router = 'R{}'.format(dst_match.group(1))

    return (src_router, dst_router)


def main():
    parser = argparse.ArgumentParser(description="create a GNS3 multi-domain topology with policies")
    parser.add_argument('-i', '--input', dest='input_topo_file', type=str, help='file with GNS3 topology description', required=True)
    parser.add_argument('-c', '--conv_time', dest='conv_time', type=int, help='number of minutes to wait for BGP convergence', default=1)
    args = parser.parse_args()

    with open(args.input_topo_file, 'r') as f:
        json_topo = ujson.load(f)

    print('Shutting down all backup links...')
    for link in json_topo['as-links']:
        if json_topo['as-links'][link]['backup'] == 'yes':
            (src_as, dst_as) = link.split('-')
            (src_router, dst_router) = extract_as_link_routers(json_topo, src_as, dst_as)
            subprocess.call([PY3_BIN, CONTROL_LINK_PY, '-i', args.input_topo_file, '-s', src_router, '-d', dst_router])

    print("Waiting for {} minutes for BGP to converge...".format(args.conv_time))
    time.sleep(60*int(args.conv_time))

    print('Reactivating all backup links...')
    for link in json_topo['as-links']:
        if json_topo['as-links'][link]['backup'] == 'yes':
            (src_as, dst_as) = link.split('-')
            (src_router, dst_router) = extract_as_link_routers(json_topo, src_as, dst_as)
            subprocess.call([PY3_BIN, CONTROL_LINK_PY, '-i', args.input_topo_file, '-s', src_router, '-d', dst_router, '-a'])

    print("Waiting for {} minutes for BGP to converge...".format(args.conv_time))
    time.sleep(60*int(args.conv_time))

    print("Checking that routing from backups happens over primaries only...")
    backups = {}
    primaries = {}

    for link in json_topo['as-links']:
        if json_topo['as-links'][link]['backup'] == 'yes':
            (src_as, dst_as) = link.split('-')
            if src_as not in backups:
                backups[src_as] = []
            backups[src_as].append(dst_as)

    for link in json_topo['as-links']:
        if json_topo['as-links'][link]['backup'] == 'no':
            (src_as, dst_as) = link.split('-')
            if src_as in backups:
                if src_as not in primaries:
                    primaries[src_as] = []
                primaries[src_as].append(dst_as)

    for asn in backups:
        for backup in backups[asn]:
            backup_id_match = re.match('AS(\d+)', backup)
            backup_id = int(backup_id_match.group(1))
            trace_start_host = 'H{}'.format(backup_id)
            telnet_ip = json_topo['gns3-nodes'][trace_start_host]['console_host']
            telnet_port = str(json_topo['gns3-nodes'][trace_start_host]['console'])

            asn_id_match = re.match('AS(\d+)', asn)
            asn_id = int(asn_id_match.group(1))
            trace_target_ip = '10.{}.0.100'.format(asn_id)

            trace_dump_file = 'trace_dump_{}_{}.json'.format(trace_start_host, trace_target_ip)
            subprocess.call([PY_BIN, GET_AS_TRACE_PY, '-ti', telnet_ip, '-tp', telnet_port, '-d', trace_target_ip, '-o', trace_dump_file])

            with open(trace_dump_file, 'r') as f:
                trace = ujson.load(f)
                # routing happens over backup
                if len(set(trace['asns']).intersection(set(primaries[asn]))) == 0:
                    print('Routing from backup {} to {} does not happen over primary connections!'.format(backup, asn))
                    print('Stopping test!')
                    sys.exit(1)

            os.remove(trace_dump_file)

    print('Shutting down all primary links...')
    for asn in primaries:
        for primary in primaries[asn]:
            (asn_router, prim_router) = extract_as_link_routers(json_topo, asn, primary)
            subprocess.call([PY3_BIN, CONTROL_LINK_PY, '-i', args.input_topo_file, '-s', asn_router, '-d', prim_router])

    print("Waiting for {} minutes for BGP to converge...".format(args.conv_time))
    time.sleep(60*int(args.conv_time))

    print('Reactivating all primary links...')
    for asn in primaries:
        for primary in primaries[asn]:
            (asn_router, prim_router) = extract_as_link_routers(json_topo, asn, primary)
            subprocess.call([PY3_BIN, CONTROL_LINK_PY, '-i', args.input_topo_file, '-s', asn_router, '-d', prim_router, '-a'])

    print("Waiting for {} minutes for BGP to converge...".format(args.conv_time))
    time.sleep(60*int(args.conv_time))

    print("Checking for wedgies...")
    wedgies = {}
    for asn in backups:
        for backup in backups[asn]:
            backup_id_match = re.match('AS(\d+)', backup)
            backup_id = int(backup_id_match.group(1))
            trace_start_host = 'H{}'.format(backup_id)
            telnet_ip = json_topo['gns3-nodes'][trace_start_host]['console_host']
            telnet_port = str(json_topo['gns3-nodes'][trace_start_host]['console'])

            asn_id_match = re.match('AS(\d+)', asn)
            asn_id = int(asn_id_match.group(1))
            trace_target_ip = '10.{}.0.100'.format(asn_id)

            trace_dump_file = 'trace_dump_{}_{}.json'.format(trace_start_host, trace_target_ip)
            subprocess.call([PY_BIN, GET_AS_TRACE_PY, '-ti', telnet_ip, '-tp', telnet_port, '-d', trace_target_ip, '-o', trace_dump_file])

            with open(trace_dump_file, 'r') as f:
                trace = ujson.load(f)
                # routing happens over backup
                if len(set(trace['asns']).intersection(set(primaries[asn]))) == 0:
                    #print('Routing from backup {} to {} does not happen over primary connections!'.format(backup, asn))
                    wedgies[asn] = {
                        'backup': backups[asn],
                        'primary': primaries[asn]
                    }

            os.remove(trace_dump_file)

    print("Following wedgies were detected!")
    pp(wedgies)


if __name__ == '__main__':
    main()
