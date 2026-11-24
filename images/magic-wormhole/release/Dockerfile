FROM python:3.15-slim

# Install system dependencies needed to compile cryptographic packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libffi-dev

# Install magic-wormhole directly
RUN pip install --no-cache-dir magic-wormhole

ENTRYPOINT ["wormhole"]