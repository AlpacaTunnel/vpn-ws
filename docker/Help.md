Deploy a vpn-ws server and a nginx server within Docker.
========================================================================================

Requirements
============

Ubuntu 16.04 (64 bit) on the vn-ws server.

Actually you can deploy the Docker containers on any machine, but since the vpn-ws image is based on `ubuntu:16.04`,
so you'd better make the vpn-ws binary file on a Ubuntu 16.04, then build the image.


Certification
=============

You'd better request your own certificate, or you can generate a self signed certificate

```sh
openssl req -x509 -nodes -days 365 -newkey rsa:2048 -keyout server.key -out server.crt
```

and replace `./nginx-ws/private/server.key` and `./nginx-ws/private/server.crt` with your new files.


Password Authentication
=======================

Add a new user

```sh
echo -n 'tom:' >> htpasswd
openssl passwd -apr1 >> htpasswd
```

and replace `./nginx-ws/private/htpasswd` with your new file.


Change URI
==========

The default URI location is `/vpn/`, you can change it in the file `./nginx-ws/sites-enabled/site-vpn`


Deploying
=========

After replace the certificate and htpasswd, you also need to make the vpn-ws binary file or download it form github, and cp it to `./vpn-ws/vpn-ws`.

then all work is done by run this command:

```sh
sudo ./deploy.sh
```

It will install Docker on the system, build the image, start a nginx server with only HTTPS, and a vpn-ws server with private IP 10.18.1.1/24.

Or you can deploy with a private IP

```sh
sudo ./deploy.sh 192.168.100.1/24
```

then you can test the URI `wss://tom:password@server_ip:443/vpn`.

That's it, thanks.
