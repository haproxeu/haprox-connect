# ARG fuer eine spaetere FROM-Zeile muss VOR dem ersten FROM stehen --
# zwischen zwei Stages deklariert (wie urspruenglich hier) gilt ein ARG
# nur fuer den Body der folgenden Stage, nicht fuer deren eigene
# FROM-Zeile (echter Fehler, beim ersten CI-Lauf gefunden: "UndefinedArgInFrom").
ARG BUILD_FROM

# Kein lego-Paket in Alpine -- per `go install` aus dem offiziellen
# Quellcode gebaut, als eigener Build-Stage, damit kein Go-Toolchain im
# finalen Image landet. 1.25 ist lego@latest's
# tatsaechliche Mindestanforderung (im ersten echten CI-Lauf mit 1.23
# gescheitert: "requires go >= 1.25.0") -- als Minor-Tag (nicht z.B.
# 1.25.3) gewaehlt, damit spaetere Patch-Releases beim naechsten
# Pflicht-Rebuild automatisch mitkommen.
FROM golang:1.25-alpine AS lego-build
RUN apk add --no-cache git
RUN GOBIN=/out go install github.com/go-acme/lego/v4/cmd/lego@latest

FROM ${BUILD_FROM}

# wireguard-tools fuer `wg`/`wg-quick`, python3 fuer enroll.py/cert.py/
# heartbeat.py, jq fuer das Auslesen von /data/haprox.json in den
# Shell-Services, nginx fuer die TLS-Terminierung, curl fuer den
# HA-Core-Proxy-Check, openssl fuer die Zertifikats-Restlaufzeit im
# Heartbeat -- sonst nichts (kein pip/requests, minimale Abhaengigkeiten).
RUN apk add --no-cache \
    wireguard-tools \
    python3 \
    jq \
    nginx \
    curl \
    openssl

# Alpines nginx-Paket bringt eine http.d/default.conf mit, die
# 0.0.0.0:80 belegt -- wegen host_network:true ist das der HOST-Port,
# nicht irgendein isoliertes Docker-Netz. Echter Bug, live auf dem
# ersten Supervised-Test gefunden: Port 80 auf einer echten HA-Box
# gehoert bereits Home Assistant Core selbst -- unsere default.conf
# haette dagegen kollidiert. Wir brauchen Port 80 nie (nur wg_ip:443),
# also die Stock-Config entfernen statt sie zu ueberschreiben.
RUN rm -f /etc/nginx/http.d/default.conf

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
