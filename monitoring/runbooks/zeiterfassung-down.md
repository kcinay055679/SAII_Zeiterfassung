# Runbook: ZeiterfassungDown

Prometheus erreicht die Zeiterfassung seit mindestens einer Minute nicht (`up{job="zeiterfassung"} == 0`). Mitarbeitende können nicht stempeln.

1. Im Repo-Ordner auf LM2 mit `docker compose ps zeiterfassung` den Zustand prüfen (`unhealthy`, `exited`, `restarting`).
2. Logs mit `docker compose logs --tail 100 zeiterfassung` lesen.
3. `/health` direkt prüfen: `curl -s localhost:8080/health`. Ein 503 nennt die Ursache, meist ein volles oder nicht beschreibbares `/data`.
4. Bei vollem Dateisystem zuerst das Runbook [LM2RootFilesystemLow](lm2-root-filesystem-low.md) abarbeiten.
5. Container mit `docker compose up -d zeiterfassung` neu starten. Das Volume `zeiterfassung-data` nicht löschen.
6. Prüfen, ob der Alert auf Resolved wechselt, und die Ursache dokumentieren.
