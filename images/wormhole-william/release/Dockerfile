FROM golang:1.26 AS build

ENV CGO_ENABLED=0
RUN go install github.com/psanford/wormhole-william@latest

FROM alpine:3
RUN apk add --no-cache ca-certificates
COPY --from=build /go/bin/wormhole-william /usr/local/bin/wormhole-william

ENTRYPOINT ["wormhole-william"]
