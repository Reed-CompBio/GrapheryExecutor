# use python 3.10 base image
FROM python:3.10

# specify working directory
WORKDIR /code

EXPOSE 7590 7590

# copy src
ADD ./ /code/executor/

RUN pip3 install /code/executor/

# run command
CMD ["graphery_executor", "server", "-u", "0.0.0.0"]
