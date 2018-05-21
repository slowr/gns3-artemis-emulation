#!/usr/bin/python3


import argparse
import telnetlib
import time
import ast


def main():
    parser = argparse.ArgumentParser(
        description='execute a command on gns3 node')
    parser.add_argument('-ti', '--tip', dest='tip', type=str,
                        help='telnet IP address', required=True)
    parser.add_argument('-tp', '--tpgort', dest='tport',
                        type=int, help='telnet port', required=True)
    parser.add_argument('-c', '--command', dest='command',
                        type=str, help='command to run', required=True)
    args = parser.parse_args()

    tn = telnetlib.Telnet(args.tip, args.tport)
    tn.write('\n'.encode('ascii'))
    time.sleep(1)
    tn.read_until('#'.encode('ascii'))

    x = ast.literal_eval(args.command)
    for cmd in x:
        tn.write('{}\n'.format(cmd).encode('ascii'))
        tn.read_until('#'.encode('ascii'))

    tn.close()


if __name__ == '__main__':
    main()
