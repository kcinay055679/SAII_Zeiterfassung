# Runbook: ZeiterfassungHighErrorRate

Mehr als 5 % der Anfragen an die Zeiterfassung enden seit mindestens fünf Minuten mit einem 5xx-Status.

1. Im Grafana-Dashboard im Panel «Zeiterfassung Fehlerquote 5xx» prüfen, seit wann die Fehler auftreten.
2. In Prometheus betroffene Endpunkte suchen: `sum by (endpoint, status) (rate(http_requests_total{job="zeiterfassung",status=~"5.."}[5m]))`.
3. Logs mit `docker compose logs --tail 200 zeiterfassung` nach Tracebacks durchsuchen.
4. `curl -s localhost:8080/health` prüfen (Datenbank und `/data`).
5. Wurde kurz vorher eine neue Version ausgerollt, auf die vorherige Version zurückgehen.
6. Prüfen, ob der Alert auf Resolved wechselt, und die Ursache dokumentieren.
