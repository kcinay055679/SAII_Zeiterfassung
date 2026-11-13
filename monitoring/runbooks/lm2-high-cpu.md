# Runbook: LM2HighCpuUsage

Die CPU-Auslastung auf LM2 liegt seit mindestens fünf Minuten über 85 %. LM2 hat nur 1 vCPU, Last wirkt sich deshalb sofort auf alle Dienste aus.

1. Im Grafana-Dashboard prüfen, seit wann die CPU-Auslastung hoch ist.
2. Auf LM2 mit `top` den verursachenden Prozess suchen.
3. Container mit `docker stats --no-stream` kontrollieren.
4. Ursache dokumentieren.
5. Einen fehlerhaften Prozess oder Container nur bei Bedarf kontrolliert neu starten.
6. Prüfen, ob der Alert auf Resolved wechselt.
