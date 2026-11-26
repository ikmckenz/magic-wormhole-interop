FROM alpine:3

RUN apk add --no-cache iptables

# eth0 is the internetwork, router joins client LANs later
ENTRYPOINT ["sh", "-c", "iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE && echo nat-ready && sleep infinity"]
