#!/usr/bin/python3

import os
import stat
import json
import argparse
import re
import copy


def extract_neighb_ip_address(this_router_num, neighb_as_num):
    neighb_ip_address = '5.{}.{}.'.format(min(this_router_num, neighb_as_num), max(this_router_num, neighb_as_num))
    if this_router_num < neighb_as_num:
        neighb_ip_address += '2'
    else:
        neighb_ip_address += '1'

    return neighb_ip_address


def main():
    parser = argparse.ArgumentParser(description='form GSN3 quagga router BGP configs')
    parser.add_argument('-i', '--input', dest='input_topo_file', type=str, help='file with input GNS3 topology description', required=True)
    parser.add_argument('-o', '--output', dest='output_router_configs', type=str, help='directory with output router configs', default='./sample_router_configs')
    args = parser.parse_args()

    with open(args.input_topo_file, 'r') as f:
        json_topo = json.load(f)

    if not os.path.isdir(args.output_router_configs):
        os.mkdir(args.output_router_configs)

    router_neighbs = {}
    router_config = {}
    for node in sorted(json_topo['gns3-nodes']):
        if re.match('^R\d+$', node):
            router_neighbs[node] = {}
            router_config[node] = ''

    for as_link in sorted(json_topo['as-links']):
        r = re.match('^AS(\d+)-AS(\d+)$', as_link)
        if r:
            src_as_num = int(r.group(1))
            dst_as_num = int(r.group(2))
            src_router = 'R{}'.format(src_as_num)
            dst_router = 'R{}'.format(dst_as_num)
            router_neighbs[src_router][dst_router] = copy.deepcopy(json_topo['as-links'][as_link])
            # reverse link
            if src_router not in router_neighbs[dst_router]:
                router_neighbs[dst_router][src_router] = copy.deepcopy(json_topo['as-links'][as_link])
                router_neighbs[dst_router][src_router]['rel'] = router_neighbs[dst_router][src_router]['rel'][::-1]
                router_neighbs[dst_router][src_router]['backup'] = 'no'

    for node in sorted(router_config):
        router_num = int(node.split('R')[1])

        # find upstreams, backups, peers, customers and monitors
        (upstreams, backups, peers, customers, monitors) = (set(), set(), set(), set(), set())
        for neighb_router in router_neighbs[node]:
            neighb_as_num = int(neighb_router.split('R')[1])
            if router_neighbs[node][neighb_router]['rel'] == 'c2p':
                if router_neighbs[node][neighb_router]['backup'] == 'yes':
                    backups.add(neighb_as_num)
                else:
                    upstreams.add(neighb_as_num)
            elif router_neighbs[node][neighb_router]['rel'] == 'p2p':
                peers.add(neighb_as_num)
            elif router_neighbs[node][neighb_router]['rel'] == 'p2c':
                customers.add(neighb_as_num)

        # Init conf
        router_config[node] += '!\n\n! credentials\nhostname bgp\npassword sdnip\n'
        router_config[node] += '\n!\n! BGP configuration\n'
        router_config[node] += '! Example from: http://www.macfreek.nl/memory/BGP_Configuration\n'

        # Router BGP conf
        router_config[node] += 'router bgp {}\n'.format(router_num)
        router_config[node] += '\tbgp router-id {}.{}.{}.{}\n'.format(router_num,
                                                                      router_num,
                                                                      router_num,
                                                                      router_num)
        router_config[node] += '\n\t! announced networks\n\tnetwork 10.{}.0.0/23\n'.format(router_num)
        router_config[node] += '\n\t! timers\n\ttimers bgp 1 3\n'
        router_config[node] += '\n\t! inbound/outbound policy\n'
        router_config[node] += '\tneighbor UPSTREAM peer-group\n'
        router_config[node] += '\tneighbor UPSTREAM route-map RM-UPSTREAM-IN in\n'
        router_config[node] += '\tneighbor UPSTREAM route-map RM-PROVIDER-OUT out\n'
        router_config[node] += '\tneighbor UPSTREAM next-hop-self\n'
        for neighb_as_num in backups:
            router_config[node] += '\tneighbor BACKUP{} peer-group\n'.format(neighb_as_num)
            router_config[node] += '\tneighbor BACKUP{} route-map RM-BACKUP-PROVIDER{}-IN in\n'.format(neighb_as_num, neighb_as_num)
            router_config[node] += '\tneighbor BACKUP{} route-map RM-BACKUP-PROVIDER{}-OUT out\n'.format(neighb_as_num, neighb_as_num)
            router_config[node] += '\tneighbor BACKUP{} next-hop-self\n'.format(neighb_as_num)
        router_config[node] += '\tneighbor PEER peer-group\n'
        router_config[node] += '\tneighbor PEER route-map RM-PEER-IN in\n'
        router_config[node] += '\tneighbor PEER route-map RM-PROVIDER-OUT out\n'
        router_config[node] += '\tneighbor PEER next-hop-self\n'
        router_config[node] += '\tneighbor CUSTOMER peer-group\n'
        router_config[node] += '\tneighbor CUSTOMER route-map RM-CUSTOMER-IN in\n'
        router_config[node] += '\tneighbor CUSTOMER next-hop-self\n'
        router_config[node] += '\tneighbor MONITOR peer-group\n'
        router_config[node] += '\tneighbor MONITOR route-map RM-MONITOR-IN in\n'
        router_config[node] += '\tneighbor MONITOR next-hop-self\n'

        router_config[node] += '\n\t! primary upstream providers\n'
        for neighb_as_num in upstreams:
            neighb_router_ip = extract_neighb_ip_address(router_num, neighb_as_num)
            router_config[node] += '\tneighbor {} remote-as {}\n'.format(neighb_router_ip, neighb_as_num)
            router_config[node] += '\tneighbor {} peer-group UPSTREAM\n'.format(neighb_router_ip)
            router_config[node] += '\tneighbor {} description Primary Transit Provider AS {}\n'.format(neighb_router_ip, neighb_as_num)
        if len(upstreams) == 0:
            router_config[node] += '\t! no primary upstream providers\n'

        router_config[node] += '\n\t! backup providers\n'
        for neighb_as_num in backups:
            neighb_router_ip = extract_neighb_ip_address(router_num, neighb_as_num)
            router_config[node] += '\tneighbor {} remote-as {}\n'.format(neighb_router_ip, neighb_as_num)
            router_config[node] += '\tneighbor {} peer-group BACKUP{}\n'.format(neighb_router_ip, neighb_as_num)
            router_config[node] += '\tneighbor {} description Backup Transit Provider AS {}\n'.format(neighb_router_ip, neighb_as_num)
        if len(backups) == 0:
            router_config[node] += '\t! no backup upstream providers\n'

        router_config[node] += '\n\t! peers\n'
        for neighb_as_num in peers:
            neighb_router_ip = extract_neighb_ip_address(router_num, neighb_as_num)
            router_config[node] += '\tneighbor {} remote-as {}\n'.format(neighb_router_ip, neighb_as_num)
            router_config[node] += '\tneighbor {} peer-group PEER\n'.format(neighb_router_ip)
            router_config[node] += '\tneighbor {} description Peer AS {}\n'.format(neighb_router_ip, neighb_as_num)
        if len(peers) == 0:
            router_config[node] += '\t! no peers\n'

        router_config[node] += '\n\t! customers\n'
        for neighb_as_num in customers:
            neighb_router_ip = extract_neighb_ip_address(router_num, neighb_as_num)
            router_config[node] += '\tneighbor {} remote-as {}\n'.format(neighb_router_ip, neighb_as_num)
            router_config[node] += '\tneighbor {} peer-group CUSTOMER\n'.format(neighb_router_ip)
            router_config[node] += '\tneighbor {} description Customer AS {}\n'.format(neighb_router_ip, neighb_as_num)
        if len(customers) == 0:
            router_config[node] += '\t! no customers\n'

        router_config[node] += '\n\t! monitors\n'
        if json_topo['as-nodes']['AS{}'.format(router_num)]['EXA']:
            router_config[node] += '\tneighbor 3.0.0.2 remote-as {}\n'.format(router_num)
        else:
            router_config[node] += '\t! no monitors\n'

        router_config[node] += '\n\t! sdn controller\n'
        if json_topo['as-nodes']['AS{}'.format(router_num)]['SDN']:
            router_config[node] += '\tneighbor 4.0.0.1 remote-as {}\n'.format(router_num)
            router_config[node] += '\tneighbor 4.0.0.1 port 2000\n'
        else:
            router_config[node] += '\t! no sdn controller\n'

        # Local Pref explanation
        router_config[node] += '\n! Local Preferences:\n'
        router_config[node] += '! We prefer traffic via customers (thay pay for it), otherwise via peers,\n'
        router_config[node] += '! and via providers only as a last resort (since we pay for that)\n'
        router_config[node] += '! 75  custom (lowered) preference, may be configured by customers, peers or providers using community 2075\n'
        router_config[node] += '! 80  providers (low preference)\n'
        router_config[node] += '! 85  custom (lowered) preference, may be configured by customers or peers using community 2085\n'
        router_config[node] += '! 90  peers (medium preference)\n'
        router_config[node] += '! 95  custom (lowered) preference, may be configured by customers using community 2095\n'
        router_config[node] += '! 100 customers (high preferences)\n'

        # Community explanation
        router_config[node] += '\n! Communities:\n'
        router_config[node] += '! We allow neighbours to announce routing entries to use with a community value that signifies\n'
        router_config[node] += '! that it is a low-preference route. This can be useful for backup connections which are not\n'
        router_config[node] += '! to be used unless there really is no other option. We never allow neighbours to set a higher\n'
        router_config[node] += '! preference: that is something we decide upon. The reason we graciously allow lower preferences\n'
        router_config[node] += '! is that we rather receive announcements with low preference than no announcement at all.\n'
        router_config[node] += '! {}:2075  (as sent by others): request to set local preference to 75\n'.format(router_num)
        router_config[node] += '! {}:2085  (as sent by others): request to set local preference to 85\n'.format(router_num)
        router_config[node] += '! {}:2095  (as sent by others): request to set local preference to 95\n'.format(router_num)
        router_config[node] += '!\n'
        router_config[node] += '! {}:3080  (set by ourself): announcement learnt from upstream provider\n'.format(router_num)
        router_config[node] += '! {}:3090  (set by ourself): announcement learnt from peer\n'.format(router_num)
        router_config[node] += '! {}:3100  (set by ourself): announcement learnt from customer\n'.format(router_num)
        router_config[node] += '! (note: our own routes have no community set)\n'

        # Route Map for upstream providers
        router_config[node] += '\n! Route map for upstream providers.\n'
        router_config[node] += '! Block bogon IPs, make entry as coming from upstream using community 3080, and\n'
        router_config[node] += '! set low local-preference\n'
        router_config[node] += '! optionally allow the neighbour to lower to local preference even more (to 75)\n'
        router_config[node] += 'route-map RM-UPSTREAM-IN deny 10\n'
        router_config[node] += '\tmatch ip address prefix-list private-ip\n'
        router_config[node] += 'route-map RM-UPSTREAM-IN permit 20\n'
        router_config[node] += '\tset community {}:3080 additive\n'.format(router_num)
        router_config[node] += '\tset local-preference 80\n'
        router_config[node] += '\ton-match next\n'
        router_config[node] += 'route-map RM-UPSTREAM-IN permit 30\n'
        router_config[node] += '\tmatch community localpref75\n'
        router_config[node] += '\tset local-preference 75\n'
        router_config[node] += 'route-map RM-UPSTREAM-IN permit 40\n'
        router_config[node] += '\t! empty route map entry, make sure all non-matching entries pass this filter\n'

        # Route Map for peers
        router_config[node] += '\n! Route map for peers.\n'
        router_config[node] += '! Block bogon IPs, make entry as coming from upstream using community 3090, and\n'
        router_config[node] += '! set medium local-preference\n'
        router_config[node] += '! optionally allow peers to lower to local preference (to 75 or 85)\n'
        router_config[node] += 'route-map RM-PEER-IN deny 10\n'
        router_config[node] += '\tmatch ip address prefix-list private-ip\n'
        router_config[node] += '\troute-map RM-PEER-IN permit 20\n'
        router_config[node] += '\tset community {}:3090 additive\n'.format(router_num)
        router_config[node] += '\tset local-preference 90\n'
        router_config[node] += '\ton-match next\n'
        router_config[node] += 'route-map RM-PEER-IN permit 30\n'
        router_config[node] += '\tmatch community localpref75\n'
        router_config[node] += '\tset local-preference 75\n'
        router_config[node] += 'route-map RM-PEER-IN permit 40\n'
        router_config[node] += '\tmatch community localpref85\n'
        router_config[node] += '\tset local-preference 85\n'
        router_config[node] += 'route-map RM-PEER-IN permit 50\n'
        router_config[node] += '\t! empty route map entry, make sure all non-matching entries pass this filter\n'

        # Outgoing Filters for peers and transit providers
        router_config[node] += '\n! Outgoing filters for peers and transit providers.\n'
        router_config[node] += '! Filter routes from other peers (we don\'t provide transit for them), only announce\n'
        router_config[node] += '! our own routes and customer routes.\n'
        router_config[node] += 'route-map RM-PROVIDER-OUT deny 10\n'
        router_config[node] += '\t! filter out route entries learnt from peers and upstream providers\n'
        router_config[node] += '\tmatch community providers\n'
        router_config[node] += 'route-map RM-PROVIDER-OUT permit 20\n'
        router_config[node] += '\t! empty route map entry, make sure all non-matching entries pass this filter\n'

        # Route Map for customers
        router_config[node] += '\n! Route map for customers.\n'
        router_config[node] += '! Block bogon IPs, make entry as coming from upstream using community 3100, and\n'
        router_config[node] += '! set a high local-preference\n'
        router_config[node] += '! optionally allow peers to lower to local preference (to 75, 85 or 95)\n'
        router_config[node] += 'route-map RM-CUSTOMER-IN deny 10\n'
        router_config[node] += '\tmatch ip address prefix-list private-ip\n'
        router_config[node] += 'route-map RM-CUSTOMER-IN permit 20\n'
        router_config[node] += '\tset community {}:3100 additive\n'.format(router_num)
        router_config[node] += '\tset local-preference 100\n'
        router_config[node] += '\ton-match next\n'
        router_config[node] += 'route-map RM-CUSTOMER-IN permit 30\n'
        router_config[node] += '\tmatch community localpref75\n'
        router_config[node] += '\tset local-preference 75\n'
        router_config[node] += 'route-map RM-CUSTOMER-IN permit 40\n'
        router_config[node] += '\tmatch community localpref85\n'
        router_config[node] += '\tset local-preference 85\n'
        router_config[node] += 'route-map RM-CUSTOMER-IN permit 50\n'
        router_config[node] += '\tmatch community localpref95\n'
        router_config[node] += '\tset local-preference 95\n'
        router_config[node] += 'route-map RM-CUSTOMER-IN permit 60\n'

        # Route Map for BGP monitors
        router_config[node] += '\n! Route map for BGP monitors.\n'
        router_config[node] += '! Block all incoming advertisements\n'
        router_config[node] += 'route-map RM-MONITOR-IN deny 10\n'

        # Community matches
        router_config[node] += '\n! community list matching route entries learnt from peers and upstream providers\n'
        router_config[node] += 'ip community-list standard providers permit {}:3080\n'.format(router_num)
        router_config[node] += 'ip community-list standard providers permit {}:3090\n'.format(router_num)
        router_config[node] += 'ip community-list standard providers deny\n'
        router_config[node] += '\n! community list matching lower preference requests\n'
        router_config[node] += 'ip community-list standard localpref75 permit {}:2075\n'.format(router_num)
        router_config[node] += 'ip community-list standard localpref85 permit {}:2085\n'.format(router_num)
        router_config[node] += 'ip community-list standard localpref95 permit {}:2095\n'.format(router_num)

        # Incoming Route Map for backup provider(s)
        for neighb_as_num in backups:
            router_config[node] += '\n! Incoming route map from backup: Set local preference to a low 75.\n'
            router_config[node] += 'route-map RM-BACKUP-PROVIDER{}-IN permit 10\n'.format(neighb_as_num)
            router_config[node] += '\t! apply regular route map for upstream providers\n'
            router_config[node] += '\t! Calling other route maps requires Quagga 0.96.5 or higher.\n'
            router_config[node] += '\tcall RM-UPSTREAM-IN\n'
            router_config[node] += '\ton-match next\n'
            router_config[node] += 'route-map RM-BACKUP-PROVIDER{}-IN permit 20\n'.format(neighb_as_num)
            router_config[node] += '\t! lower local-preference from 80 to 75 for backup connections\n'
            router_config[node] += '\tset local-preference 75\n'

        # Outgoing Route Map for backup provider(s)
        for neighb_as_num in backups:
            router_config[node] += '\n! Outgoing route map for backup connections\n'
            router_config[node] += '! Ask peer to set their local preference to a low 75.\n'
            router_config[node] += 'route-map RM-BACKUP-PROVIDER{}-OUT permit 10\n'.format(neighb_as_num)
            router_config[node] += '\t! apply regular route map for upstream providers\n'
            router_config[node] += '\tcall RM-PROVIDER-OUT\n'
            router_config[node] += '\ton-match next\n'
            router_config[node] += 'route-map RM-BACKUP-PROVIDER{}-OUT permit 20\n'.format(neighb_as_num)
            router_config[node] += '\t! set community that asks AS {} to use a lower preference.\n'.format(neighb_as_num)
            router_config[node] += '\t! communities are send, but since we don\'t add but replace the community here,\n'
            router_config[node] += '\t! private communities such as 3XXX are never announced to neighbors.\n'
            router_config[node] += '\tset community {}:2075\n'.format(neighb_as_num)

        # Prefix Lists
        router_config[node] += '\n! Prefix list matching private IP ranges, bogons, and other suspicious IP range announcements.\n'
        router_config[node] += '! Any \'permit\' here is a match (not really a \'permit\') which is BLOCKED in incoming route map.\n'
        router_config[node] += '! Note: The le 32 also filters subnets of these bogon ranges. However, neigbours can still\n'
        router_config[node] += '! announce a large supernet which contains a bogon range (e.g. 169.254.0.0/15). So you likely\n'
        router_config[node] += '! want to do additional per-neighbour filtering, or peer with known bogon black hole servers.\n'
        router_config[node] += 'ip prefix-list private-ip description Private ranges, large or small IP ranges\n'
        router_config[node] += 'ip prefix-list private-ip permit 0.0.0.0/8 le 32\n'
        router_config[node] += '! no filtering on 10.0.0.0 range for demo network\n'
        router_config[node] += '!ip prefix-list private-ip permit 10.0.0.0/8 le 32\n'
        router_config[node] += 'ip prefix-list private-ip permit 127.0.0.0/8 le 32\n'
        router_config[node] += 'ip prefix-list private-ip permit 169.254.0.0/16 le 32\n'
        router_config[node] += 'ip prefix-list private-ip permit 172.16.0.0/12 le 32\n'
        router_config[node] += 'ip prefix-list private-ip permit 192.0.2.0/24 le 32\n'
        router_config[node] += 'ip prefix-list private-ip permit 192.168.0.0/16 le 32\n'
        router_config[node] += 'ip prefix-list private-ip permit 240.0.0.0/4 le 32\n'
        router_config[node] += '! filter more specifics\n'
        router_config[node] += 'ip prefix-list private-ip permit 0.0.0.0/0 ge 26\n'
        router_config[node] += 'ip prefix-list private-ip deny any\n'

        # End conf
        router_config[node] += '\n!\nlog stdout'

    with open('{}/zebra.conf'.format(args.output_router_configs), 'w') as f:
        f.write('! Configuration for zebra (NB: it is the same for all routers)\n!\nhostname zebra\npassword sdnip\nlog stdout')

    with open('{}/disable_rp_filter'.format(args.output_router_configs), 'w') as f:
        f.write('#!/bin/sh\n\n')
        f.write('echo 0 > "/proc/sys/net/ipv4/conf/$IFACE/rp_filter"\n')
        f.write('echo 0 > "/proc/sys/net/ipv4/conf/all/rp_filter"\n')
        f.write('echo 0 > "/proc/sys/net/ipv4/conf/default/rp_filter"\n')
        os.chmod('{}/disable_rp_filter'.format(args.output_router_configs), 0o775)

    for node in sorted(router_config):
        with open('{}/{}_bgpd.conf'.format(args.output_router_configs, node), 'w') as f:
            f.write(router_config[node])


if __name__ == '__main__':
    main()
