#!/usr/bin/with-contenv bashio
# Ruft die eigentliche Enrollment-/Zustandslogik auf (Python, siehe
# usr/bin/enroll.py). Schlaegt enroll.py fehl (Code fehlt/ungueltig,
# siehe dort), bricht cont-init.d damit den Add-on-Start klar ab --
# kein Weiterlaufen mit halbem Zustand.
bashio::log.info "Pruefe Enrollment-Zustand..."
python3 /usr/bin/enroll.py
