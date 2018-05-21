#!/usr/bin/python3

import os
import argparse
# import paramiko

USER = 'gns3'
PASS = 'gns3'

def main():
    parser = argparse.ArgumentParser(description='copy file to remote server')
    parser.add_argument('-f', '--file', dest='local_file', type=str, help='file to copy', required=True)
    parser.add_argument('-i', '--ip', dest='server_ip', type=str, help='ip of remote server', default='172.16.42.128')
    parser.add_argument('-p', '--path', dest='server_path', type=str, help='file path of remote server', required=True)
    args = parser.parse_args()

    os.system('sshpass -p {} scp {} {}@{}:{}'.format(PASS, args.local_file, USER, args.server_ip, args.server_path))
    # TODO: fix paramiko!!!
    # ssh = paramiko.SSHClient()
    # ssh.load_system_host_keys()
    # ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    # ssh.connect(args.server_ip, username=USER, password=PASS)
    # sftp = ssh.open_sftp()
    # sftp.put(args.file, args.server_path)
    # sftp.close()
    # ssh.close()

if __name__ == '__main__':
    main()
