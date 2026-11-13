# Runbook: ZeiterfassungSlowStamps

Das p95 der Stempelanfragen (`POST /stamp`) liegt seit mindestens zehn Minuten über 500 ms. Das verletzt das Latenz-SLO.

1. Im Grafana-Dashboard prüfen, ob gleichzeitig CPU oder RAM von LM2 hoch sind. LM2 hat nur 1 vCPU.
2. Wenn ja, das Runbook [LM2HighCpuUsage](lm2-high-cpu.md) oder [LM2HighMemoryUsage](lm2-high-memory.md) abarbeiten.
3. Mit `docker stats --no-stream` prüfen, welcher Container die Last erzeugt.
4. Request-Rate im Dashboard prüfen: ungewöhnlich viele Anfragen deuten auf einen Lasttest oder Missbrauch hin.
5. Ursache dokumentieren. Die Zeiterfassung nur bei Bedarf mit `docker compose restart zeiterfassung` neu starten.
6. Prüfen, ob der Alert auf Resolved wechselt.
