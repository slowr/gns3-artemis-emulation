#!/usr/bin/python


import re
import argparse
import ujson
import telnetlib
import time


def main():
    parser = argparse.ArgumentParser(description="execute and parse traceroute on gns3 node")
    parser.add_argument('-ti', '--tip', dest='tip', type=str, help='telnet IP address', required=True)
    parser.add_argument('-tp', '--tpgort', dest='tport', type=int, help='telnet port')
    parser.add_argument('-d', '--dest', dest='dest', type=str, help='traceroute destination')
    parser.add_argument('-o', '--out_file', dest='out_json', type=str, help='output json file with list of ASNs in-path')
    args = parser.parse_args()

    tn = telnetlib.Telnet(args.tip, args.tport)
    tn.write('\n')
    time.sleep(1)
    tn.close()
    time.sleep(1)
    tn = telnetlib.Telnet(args.tip, args.tport)
    tn.write('\n')
    time.sleep(1)
    tn.read_until('#')
    tn.write('traceroute {}\n'.format(args.dest))
    raw_trace_data = tn.read_until('#')
    tn.close()

    # sample result:
    #    [' \x1b[6ntraceroute 10.2.0.100',
    # 'traceroute to 10.2.0.100 (10.2.0.100), 30 hops max, 46 byte packets',
    # ' 1  10.1.0.1 (10.1.0.1)  0.917 ms  1.051 ms  0.429 ms',
    # ' 2  10.1.4.2 (10.1.4.2)  0.661 ms  0.939 ms  0.204 ms',
    # ' 3  10.2.3.2 (10.2.3.2)  0.307 ms  1.676 ms  0.821 ms',
    # ' 4  10.1.2.2 (10.1.2.2)  0.493 ms  0.386 ms  0.006 ms',
    # ' 5  10.2.0.100 (10.2.0.100)  0.005 ms  0.489 ms  0.303 ms',
    # '/ #']
    lined_trace_data = raw_trace_data.split('\r\n')

    # sample hop_ips
    # ['10.1.0.1', '10.1.4.2', '10.2.3.2', '10.1.2.2', '10.2.0.100']
    hop_ips = []
    traceroute_section = False
    for line in lined_trace_data:
        traceroute_start = re.match('^traceroute\s+to\s+\S*\s*\((\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\).*', line)
        if traceroute_start:
            traceroute_section = True
            continue

        if traceroute_section:
           hop_ip_match = re.match('\s*\d+\s+(?:\S+)?\s*\((\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\)\s+.*', line)
           if hop_ip_match:
               hop_ip = hop_ip_match.group(1)
               hop_ips.append(hop_ip)

    # sample hop_asns
    # ['AS1', 'AS4', 'AS3', 'AS2']
    hop_asns = []
    for hop_ip in hop_ips:
        octet_strs = hop_ip.split('.')
        second_octet = int(octet_strs[1])
        third_octet = int(octet_strs[2])
        fourth_octet = int(octet_strs[3])
        hop_asn = None
        if third_octet == 0:
            hop_asn = 'AS{}'.format(second_octet)
        else:
            if fourth_octet == 1:
                hop_asn = 'AS{}'.format(second_octet)
            else:
                hop_asn = 'AS{}'.format(third_octet)
        if hop_asn is not None and hop_asn not in hop_asns:
            hop_asns.append(hop_asn)

    d = {
        'ips': hop_ips,
        'asns': hop_asns
    }
    with open(args.out_json, 'w') as f:
        ujson.dump(d, f)


if __name__ == '__main__':
    main()
