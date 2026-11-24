FROM python:3.15-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    git \
    build-essential \
    libffi-dev \
    libssl-dev && \
    rm -rf /var/lib/apt/lists/*

# Clone and install magic-wormhole-transit-relay from the latest master branch
RUN git clone --depth 1 https://github.com/magic-wormhole/magic-wormhole-transit-relay.git /tmp/magic-wormhole-transit-relay && \
    cd /tmp/magic-wormhole-transit-relay && \
    pip install --no-cache-dir --break-system-packages . && \
    rm -rf /tmp/magic-wormhole-transit-relay

RUN mkdir -p /var/lib/transit

EXPOSE 4001

# The usage database is on disk so tests can inspect connections: each pair of
# glued sockets is recorded there once both sides have hung up.
ENTRYPOINT ["twist", "transitrelay", "--usage-db=/var/lib/transit/usage.sqlite"]
