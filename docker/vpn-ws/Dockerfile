FROM ubuntu:16.04

MAINTAINER twitter.com/alpacatunnel

RUN apt-get update && \
    apt-get install iproute2 -y && \
	apt-get install iptables -y && \
    apt-get clean

COPY vpn-ws /usr/bin/
COPY vpn.sh /usr/bin/

CMD ["sh", "/usr/bin/vpn.sh"]

