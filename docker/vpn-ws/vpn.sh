#!/bin/sh

private_ip=10.0.0.1/24
[ "x$1" != "x" ] && private_ip=$1

vpn_log=/tmp/vpn-ws/vpn-ws.log

ip tuntap add dev ws0 mode tap
[ $? != 0 ] && \
    echo "add tap interface failed inside container." > $vpn_log && \
    exit 1

ip link set ws0 up
ip addr add $private_ip dev ws0
[ $? != 0 ] && \
    echo "add address to interface failed inside container." > $vpn_log && \
    exit 1


iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE
[ $? != 0 ] && \
    echo "add iptables rule failed inside container." > $vpn_log && \
    exit 1


vpn-ws --tuntap ws0 /tmp/vpn-ws/vpn.sock
[ $? != 0 ] && \
    echo "start vpn-ws failed inside container." > $vpn_log && \
    exit 1

