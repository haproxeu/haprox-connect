ARG BUILD_FROM
FROM ${BUILD_FROM}

# wireguard-tools fuer `wg`/`wg-quick`, python3 fuer enroll.py, jq fuer
# das Auslesen von /data/haprox.json im wireguard-Service -- sonst
# nichts (kein pip/requests, siehe CLAUDE.md-Philosophie des
# Schwester-Repos /root/haprox).
RUN apk add --no-cache \
    wireguard-tools \
    python3 \
    jq

COPY rootfs /

RUN chmod a+x /etc/cont-init.d/10-enroll.sh \
    /etc/services.d/wireguard/run \
    /etc/services.d/wireguard/finish \
    /usr/bin/enroll.py
