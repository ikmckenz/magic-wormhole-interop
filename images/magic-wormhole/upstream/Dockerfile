FROM python:3.15-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    git \
    build-essential \
    iproute2 \
    libffi-dev \
    libssl-dev && \
    rm -rf /var/lib/apt/lists/*

# Clone and install magic-wormhole from the latest master branch
RUN git clone --depth 1 https://github.com/magic-wormhole/magic-wormhole.git /tmp/magic-wormhole && \
    cd /tmp/magic-wormhole && \
    pip install --no-cache-dir --break-system-packages . && \
    rm -rf /tmp/magic-wormhole

ENTRYPOINT ["wormhole"]
