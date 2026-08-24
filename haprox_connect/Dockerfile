# ARG fuer eine spaetere FROM-Zeile muss VOR dem ersten FROM stehen --
# zwischen zwei Stages deklariert (wie urspruenglich hier) gilt ein ARG
# nur fuer den Body der folgenden Stage, nicht fuer deren eigene
# FROM-Zeile (echter Fehler, beim ersten CI-Lauf gefunden: "UndefinedArgInFrom").
ARG BUILD_FROM

# Kein lego-Paket in Alpine -- wie am Relay per `go install` gebaut
# (siehe /root/haprox/README.md), aber als eigener Build-Stage, damit
# kein Go-Toolchain im finalen Image landet.
FROM golang:1.23-alpine AS lego-build
RUN apk add --no-cache git
RUN GOBIN=/out go install github.com/go-acme/lego/v4/cmd/lego@latest

FROM ${BUILD_FROM}

# wireguard-tools fuer `wg`/`wg-quick`, python3 fuer enroll.py/cert.py/
# heartbeat.py, jq fuer das Auslesen von /data/haprox.json in den
# Shell-Services, nginx fuer die TLS-Terminierung, curl fuer den
# HA-Core-Proxy-Check, openssl fuer die Zertifikats-Restlaufzeit im
# Heartbeat -- sonst nichts (kein pip/requests, siehe
# CLAUDE.md-Philosophie des Schwester-Repos /root/haprox).
RUN apk add --no-cache \
    wireguard-tools \
    python3 \
    jq \
    nginx \
    curl \
    openssl

COPY --from=lego-build /out/lego /usr/local/bin/lego
COPY rootfs /

RUN chmod a+x /etc/cont-init.d/10-enroll.sh \
    /etc/services.d/wireguard/run \
    /etc/services.d/wireguard/finish \
    /etc/services.d/cert/run \
    /etc/services.d/nginx/run \
    /etc/services.d/heartbeat/run \
    /usr/bin/enroll.py \
    /usr/bin/cert.py \
    /usr/bin/heartbeat.py
