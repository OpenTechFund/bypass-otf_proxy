FROM ubuntu:18.04

# Update ubuntu
RUN apt-get update
RUN apt-get dist-upgrade

# get needed packages
RUN apt-get install nginx wget

COPY default.conf /etc/nginx/conf.d/default.conf

ADD start.sh /start.sh
ADD wget.sh /wget.sh
RUN chmod 700 /wget.sh

EXPOSE 80

CMD ["./start.sh"]
CMD ["./wget.sh"]