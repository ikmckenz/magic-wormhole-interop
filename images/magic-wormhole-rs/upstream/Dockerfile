FROM rust:1-alpine AS build

RUN apk add --no-cache git musl-dev

RUN git clone --depth 1 https://github.com/magic-wormhole/magic-wormhole.rs /src/wormhole-rs
WORKDIR /src/wormhole-rs
RUN cargo install --locked --path cli --root /usr/local

FROM alpine:3
RUN apk add --no-cache ca-certificates

COPY --from=build /usr/local/bin/wormhole-rs /usr/local/bin/wormhole-rs

ENTRYPOINT ["wormhole-rs"]
