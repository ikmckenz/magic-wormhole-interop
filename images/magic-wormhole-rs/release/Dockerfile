FROM rust:1-alpine AS build

RUN apk add --no-cache musl-dev
RUN cargo install magic-wormhole-cli --locked --root /usr/local

FROM alpine:3
RUN apk add --no-cache ca-certificates
COPY --from=build /usr/local/bin/wormhole-rs /usr/local/bin/wormhole-rs

ENTRYPOINT ["wormhole-rs"]
