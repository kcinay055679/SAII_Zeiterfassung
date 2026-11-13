# Runbook: LM2RootFilesystemLow

Auf dem Root-Dateisystem `/` von LM2 sind seit mindestens zehn Minuten weniger als 15 % frei. Ist `/` voll, können Prometheus, Docker und die Datenbank nicht mehr schreiben.

1. Im Grafana-Dashboard prüfen, wie schnell der freie Platz sinkt (langsam = Wachstum, schnell = Fehler).
2. Auf LM2 mit `df -h /` den aktuellen Stand prüfen.
3. Grösste Verzeichnisse suchen: `sudo du -xh / --max-depth=2 | sort -h | tail -20`.
4. Docker-Belegung prüfen: `docker system df`. Ungenutzte Images mit `docker image prune` entfernen.
5. Logs prüfen: `journalctl --disk-usage`, bei Bedarf `sudo journalctl --vacuum-size=500M`.
6. Keine Daten von Prometheus, Grafana oder der Zeiterfassung löschen. Ursache dokumentieren.
7. Prüfen, ob der Alert auf Resolved wechselt.
