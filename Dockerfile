# use python 3.9 base image
FROM python:3.10

# specify working directory
WORKDIR /code

ENV GRAPHERY_EXECUTOR_DEFAULT_SERVE_URL="0.0.0.0"
EXPOSE 7590 7590

# make cache folder
RUN mkdir /code/graphery_cache
ENV CONTROLLER_CACHE_PATH="/code/graphery_cache"

# copy src
ADD ./executor /code/executor/

RUN python3 /code/executor/setup.py install

# run command
CMD ['graphery_executor']
