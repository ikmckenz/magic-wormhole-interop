FROM python:3.15-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    git \
    build-essential \
    libffi-dev \
    libssl-dev && \
    rm -rf /var/lib/apt/lists/*

COPY . /tmp/magic-wormhole
RUN pip install --no-cache-dir --break-system-packages /tmp/magic-wormhole && \
    rm -rf /tmp/magic-wormhole

ENTRYPOINT ["wormhole"]
