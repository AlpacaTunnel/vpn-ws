FROM nginx:1.11.10-alpine

MAINTAINER twitter.com/alpacatunnel

COPY nginx.conf /etc/nginx/
COPY index.html /var/www/html/
COPY sites-enabled/ /etc/nginx/sites-enabled/

COPY private/ /etc/nginx/private/

EXPOSE 443

CMD ["nginx", "-g", "daemon off;"]

