#!/usr/bin/python3

# Author: twitter.com/alpacatunnel
# TBD: monitor route/tunnel, chnroute


import os
import re
import sys
import json
import time
import subprocess
import threading
import ipaddress
import logging
from pprint import pprint

LOGFILE = '/tmp/vpn-monitor.log'
CONF_NAME = 'vpn-monitor.json'

formatter = '%(asctime)s %(levelname)s %(module)s:%(funcName)s:%(lineno)d - %(message)s'
logging.basicConfig(filename=LOGFILE, format=formatter, level=logging.INFO)
logger = logging.getLogger()


def exec_cmd(cmd, split=False, realtime_print=False):
    """
    run the cmd until terminated.
    """

    cmd_list = cmd.split()
    child = subprocess.Popen(cmd_list, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)

    stream = ''

    # Poll process for new output until finished
    while child.poll() is None:
        line = child.stdout.readline()
        if realtime_print:
            sys.stdout.write(line)
            sys.stdout.flush()
        else:
            stream += line

    stream += child.communicate()[0]

    rc = child.returncode

    if split:
        data = (stream.split('\n'))
    else:
        data = stream

    return (rc, data)


def get_conf():
    cur_dir = os.path.dirname(os.path.realpath(__file__))
    
    if cur_dir == '/usr/local/bin':
        conf_path = '/usr/local/etc'
    elif cur_dir == '/usr/bin':
        conf_path = '/etc'
    else:
        conf_path = cur_dir
    
    conf_file = os.path.join(conf_path, CONF_NAME)

    with open(conf_file) as data_file:
        conf = json.load(data_file)
    
    return conf


class Tunnel():

    """
    A class to manage the tuntap interface.

    :param str name:
        name of the tunnel

    :param str mode:
        mode of the tunnel, tun or tap

    :param int mtu:
        mtu of the tunnel, must less than 1408

    :param ipaddress.IPv4Interface IPv4:
        IPv4 address and mask, the mask better be 16

    :param ipaddress.IPv6Interface IPv6:
        IPv6 address and mask
    """

    MIN_MTU = 68
    MAX_MTU = 9000
    DEFAULT_MTU = 1500
    DEFAULT_MODE = 'tun'

    def __init__(self, name, mode=None, mtu=None, IPv4=None, IPv6=None):
        self.name  = str(name)
        self._mode = mode
        self._mtu  = mtu
        self._IPv4 = IPv4
        self._IPv6 = IPv6

    @property
    def mode(self):
        if self._mode:
            return self._mode
        else:
            return self.__class__.DEFAULT_MODE

    @mode.setter
    def mode(self, mode):
        mode = str(mode)
        if mode.lower() not in ['tun', 'tap']:
            raise ValueError('mode must be tun or tap')
        self._mode = mode

    @property
    def mtu(self):
        if self._mtu:
            return self._mtu
        else:
            return self.__class__.DEFAULT_MTU

    @mtu.setter
    def mtu(self, mtu):
        mtu = int(mtu)
        if mtu > self.__class__.MAX_MTU or mtu < self.__class__.MIN_MTU:
            raise ValueError('mtu must be between %d and %d' % (self.__class__.MIN_MTU, self.__class__.MAX_MTU))
        self._mtu = mtu

    @property
    def IPv4(self):
        return self._IPv4

    @IPv4.setter
    def IPv4(self, ip):
        if not isinstance(ip, ipaddress.IPv4Interface):
            raise ValueError('%s is not instance of ipaddress.IPv4Interface' % ip)
        self._IPv4 = ip

    @property
    def IPv6(self):
        return self._IPv6

    @IPv6.setter
    def IPv6(self, ip):
        if not isinstance(ip, ipaddress.IPv6Interface):
            raise ValueError('%s is not instance of ipaddress.IPv6Interface' % ip)
        self._IPv6 = ip

    def _cmd(self, c, split=False):
        return exec_cmd(c, split)
    
    def _exists(self):
        '''
        return True if tunif exists
        '''
        rc, interfaces = self._cmd('ip link', True)
        if rc != 0:
            raise Exception('cmd `ip link` error: %s' % interfaces)
        for line in interfaces:
            re_obj = re.match(r'^[0-9]+:\s+(.*?):\s+<', line)
            if re_obj:
                interface = re_obj.group(1)
                if interface == self.name:
                    return True
        return False

    def _ipv4_overlaps(self):
        rc, ip_addrs = self._cmd('ip -4 addr', True)
        if rc != 0:
            raise Exception('cmd `ip -4 addr` error: %s' % ip_addrs)
        for line in ip_addrs:
            line = line.lstrip()
            if line.startswith('inet'):
                re_obj = re.match(r'^inet\s+(.*?)\s', line)
                if re_obj:
                    inet4 = ipaddress.IPv4Network(re_obj.group(1), False)
                    if self.IPv4:
                        inet4_self = ipaddress.IPv4Network(self.IPv4, False)
                        if inet4.overlaps(inet4_self):
                            return True
        return False

    def _ipv6_overlaps(self):
        rc, ip_addrs = self._cmd('ip -6 addr', True)
        if rc != 0:
            raise Exception('cmd `ip -6 addr` error: %s' % ip_addrs)
        for line in ip_addrs:
            line = line.lstrip()
            if line.startswith('inet6'):
                re_obj = re.match(r'^inet6\s+(.*?)\s', line)
                if re_obj:
                    inet6 = ipaddress.IPv6Network(re_obj.group(1), False)
                    if self.IPv6:
                        inet6_self = ipaddress.IPv6Network(self.IPv6, False)
                        if inet6.overlaps(inet6_self):
                            return True
        return False

    def _add_ipv4(self):
        if self._ipv4_overlaps():
            raise Exception('tunnel %s: IPv4 overlaps with other interface, cannot add IP' % self.name)
        c = 'ip -4 addr add %s dev %s' % (self.IPv4, self.name)
        rc, output = self._cmd(c)
        if rc != 0:
            raise Exception('cmd `%s` error: %s' % (c, output))

    def _add_ipv6(self):
        if self._ipv6_overlaps():
            raise Exception('tunnel %s: IPv6 overlaps with other interface, cannot add IP' % self.name)
        c = 'ip -6 addr add %s dev %s' % (self.IPv6, self.name)
        rc, output = self._cmd(c)
        if rc != 0:
            raise Exception('cmd `%s` error: %s' % (c, output))

    def _add_dev(self):
        if self._exists():
            raise Exception('tunnel %s already exists, nothing to do!' % self.name)
        c = 'ip tuntap add dev %s mode %s' % (self.name, self.mode)
        rc, output = self._cmd(c)
        if rc != 0:
            raise Exception('cmd `%s` error: %s' % (c, output))
        self._cmd('ip link set %s up' % self.name)
        if not self._exists():
            raise Exception('add tunnel %s failed: %s'% (self.name, output))

    def _set_mtu(self):
        c = 'ip link set %s mtu %d' % (self.name, self.mtu)
        rc, output = self._cmd(c)
        if rc != 0:
            raise Exception('cmd `%s` error: %s' % (c, output))

    def _del_dev(self):
        if self._exists():
            c = 'ip tuntap del dev %s mode %s' % (self.name, self.mode)
            rc, output = self._cmd(c)
            if rc != 0:
                raise Exception('cmd `%s` error: %s' % (c, output))

    def add(self):
        self._add_dev()
        self._set_mtu()
        if self.IPv4:
            self._add_ipv4()
        if self.IPv6:
            self._add_ipv6()

    def delete(self):
        self._del_dev()


class Instance(threading.Thread):
    """
    An Instance is a running VPN process.
    """

    def __init__(self, type=None, conf_dict=None):
        self.type = type
        self.conf_dict = conf_dict
        super(Instance, self).__init__()

    def run(self):
        while True:
            try:
                if self.type == 'vpn-ws':
                    self.vpn_ws()
            except Exception as e:
                logger.error(str(e))
            finally:
                time.sleep(1)

    def vpn_ws(self):
        tun_name = self.conf_dict['name']
        server_url = self.conf_dict['server_url']
        
        cur_dir = os.path.dirname(os.path.realpath(__file__))
        vpn_ws_client = os.path.join(cur_dir, 'vpn-ws-client')

        cmd = '%s --no-verify %s %s' % (vpn_ws_client, tun_name, server_url)

        exec_cmd(cmd, realtime_print=True)


def start():
    conf = get_conf()

    tunnel = conf['tunnels'][0]

    tun = Tunnel(tunnel['name'], 'tap')
    tun.IPv4 = ipaddress.IPv4Interface(tunnel['client_private_ip'])
    tun.delete()
    tun.add()

    vpn = Instance(type=tunnel['type'], conf_dict=tunnel)
    vpn.start()

    while True:
        # print('wait in main thread')
        sys.stdout.flush()
        time.sleep(1)

    vpn.join()


start()

