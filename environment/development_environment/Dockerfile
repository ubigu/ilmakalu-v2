FROM ubuntu:20.04

RUN apt-get update && apt install -y software-properties-common && add-apt-repository ppa:deadsnakes/ppa
RUN apt-get install -y \
    python-is-python3 \
    python3.10 \
    python3.10-venv \
    python3.10-dev \
    build-essential \
    autoconf \
    libtool \
    git

ENTRYPOINT [ "bash" ]