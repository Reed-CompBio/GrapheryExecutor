# use python 3.10 base image
FROM python:3.10.2-alpine

# specify working directory
WORKDIR /code

EXPOSE 7590 7590

# copy src
ADD ./ /code/executor/

# install requirements
RUN apk add git && pip3 install /code/executor/

# RUN sudo iptables -P OUTPUT DROP \
#    && sudo iptables -A OUTPUT -p tcp -s 192.168.0.0/24 --dport 7590 -j ACCEPT \
#    && sudo iptables -A OUTPUT -p udp -s 192.168.0.0/24 --dport 7590 -j ACCEPT

# run command
ENTRYPOINT ["graphery_executor", "server", "-u", "0.0.0.0"]
