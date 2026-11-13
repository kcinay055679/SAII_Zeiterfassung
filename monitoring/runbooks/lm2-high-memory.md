# Runbook: LM2HighMemoryUsage

Die RAM-Auslastung auf LM2 liegt seit mindestens fünf Minuten über 85 %.

1. Im Grafana-Dashboard «LM2 und Zeiterfassung» prüfen, seit wann der RAM-Verlauf steigt.
2. Auf LM2 mit `free -h` den freien Speicher prüfen.
3. Mit `top` (Taste `M`) den Prozess mit dem grössten Speicherbedarf suchen.
4. Container mit `docker stats --no-stream` kontrollieren.
5. Ursache dokumentieren. Einen fehlerhaften Prozess oder Container nur bei Bedarf kontrolliert neu starten.
6. Prüfen, ob der Alert auf Resolved wechselt.
