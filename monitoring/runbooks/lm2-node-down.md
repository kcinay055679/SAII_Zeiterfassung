# Runbook: LM2NodeDown

Prometheus erreicht den Node Exporter auf LM2 seit mindestens einer Minute nicht (`up{job="lm2-node"} == 0`).

1. In Prometheus unter `/targets` die Fehlermeldung beim Target `lm2-node` lesen.
2. Prüfen, ob LM2 per SSH erreichbar ist. Wenn nicht: VM-Konsole in Smartlearn öffnen.
3. Auf LM2 im Ordner `monitoring-lm2` mit `docker compose ps` den Zustand von `saii-node-exporter` prüfen.
4. Logs mit `docker compose logs --tail 50 node-exporter` ansehen.
5. Container mit `docker compose start node-exporter` starten.
6. Prüfen, ob der Alert auf Resolved wechselt, und die Ursache dokumentieren.
