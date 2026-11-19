FROM python:3.15-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    git \
    build-essential \
    libffi-dev \
    libssl-dev && \
    rm -rf /var/lib/apt/lists/*

# Clone and install magic-wormhole-mailbox-server from the latest master branch
RUN git clone --depth 1 https://github.com/magic-wormhole/magic-wormhole-mailbox-server.git /tmp/magic-wormhole-mailbox-server && \
    cd /tmp/magic-wormhole-mailbox-server && \
    pip install --no-cache-dir --break-system-packages . && \
    rm -rf /tmp/magic-wormhole-mailbox-server

RUN mkdir -p /var/lib/mailbox

EXPOSE 4000

# The state database is on disk so tests can inspect reservations: with the
# default --blur-usage=None the server also logs nameplate creation.
ENTRYPOINT ["twist", "wormhole-mailbox", "--channel-db=/var/lib/mailbox/relay.sqlite", "--usage-db=/var/lib/mailbox/usage.sqlite"]
