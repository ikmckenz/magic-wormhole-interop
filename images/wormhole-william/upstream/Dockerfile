FROM golang:1.26 AS build

ENV CGO_ENABLED=0
RUN git clone --depth 1 --branch master https://github.com/psanford/wormhole-william /src/william
WORKDIR /src/william
RUN go build -o /usr/local/bin/wormhole-william .

FROM alpine:3
RUN apk add --no-cache ca-certificates
COPY --from=build /usr/local/bin/wormhole-william /usr/local/bin/wormhole-william

ENTRYPOINT ["wormhole-william"]
