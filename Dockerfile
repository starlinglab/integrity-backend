FROM debian:bullseye

RUN apt update && apt install -y python3 python3-pip && pip3 install pipenv
