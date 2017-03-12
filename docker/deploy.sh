#!/bin/bash
export PATH="/bin:/sbin:/usr/sbin:/usr/bin:/usr/local/bin"

private_ip=10.18.1.1/24
[ "x$1" != "x" ] && private_ip=$1

vpn_bin=vpn-ws/vpn-ws
vpn_log=/tmp/vpn-ws/vpn-ws.log

[ ! -x "$vpn_bin" ] && \
    echo "File '$vpn_bin' is not executable or not found." && \
    exit 1


[ ! "$(docker -v)" ] && \
    echo "Installing docker..." && \
    curl -sSL https://get.docker.com/ | sh

[ ! "$(docker -v)" ] && \
    echo "install docker failed" && \
    exit 1


echo "Building nginx-ws..."
docker build nginx-ws -t nginx-ws:latest
[ $? != 0 ] && echo "build nginx-ws failed" && exit 1


echo "Building vpn-ws..."
docker build vpn-ws -t vpn-ws:latest
[ $? != 0 ] && echo "build vpn-ws failed" && exit 1


rm -rf /tmp/vpn-ws/
mkdir -p /tmp/vpn-ws/
[ $? != 0 ] && echo "mkdir /tmp/vpn-ws/ failed" && exit 1

echo "Starting vpn-ws..."
vpn_id=`docker run --privileged --cap-add=NET_ADMIN -d -v /tmp/vpn-ws/:/tmp/vpn-ws/ vpn-ws:latest /usr/bin/vpn.sh $private_ip`
sleep 1
docker ps -f id=$vpn_id | grep "vpn-ws"
[ $? != 0 ] && echo "start vpn-ws failed" && \
    docker rm -f $vpn_id && \
    cat $vpn_log && \
    exit 1

echo "Starting nginx-ws..."
nginx_id=`docker run -d -v /tmp/vpn-ws/:/tmp/vpn-ws/ -p 443:443/tcp nginx-ws:latest`
sleep 1
docker ps -f id=$nginx_id | grep "nginx-ws"
[ $? != 0 ] && echo "start nginx-ws failed" && \
    docker rm -f $vpn_id && \
    docker rm -f $nginx_id && \
    exit 1


echo "Done."

