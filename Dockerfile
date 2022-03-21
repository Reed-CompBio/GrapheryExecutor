# use python 3.10 base image
FROM python:3.10.2-alpine

# specify working directory
WORKDIR /code

EXPOSE 7590 7590

# copy src
ADD ./ /code/

# install requirements
RUN apk add git iptables ip6tables && pip3 install /code/ \
    && adduser --disabled-password -g "executor" executor

# run command
ENTRYPOINT ["/bin/sh", "/code/setup.sh"]
