# Decisions

Everything settled while planning, in one place. The ones that are hard to reverse have an ADR in [adr/](adr/). Terms are defined in [CONTEXT.md](../CONTEXT.md).

## Scope and process

| # | Decision | Notes |
| --- | --- | --- |
| 1 | Built with Claude Code, no Hermes | [ADR-0005](adr/0005-claude-code-instead-of-hermes.md) |
| 2 | Lives in `zeiterfassung/` next to `kubernetes-demo-minikube/`, which is the reference | Course path `~/workspace/zeiterfassung` not used |
| 3 | Order of work: app and cluster first, docs afterwards | |
| 4 | Group project (26A Gruppe 6) | Authors: Yogani Y., Luca G., Yanick M. |
| 5 | Git history with conventional commits, committed in small steps | HowTo asks for a traceable history |

## Functionality

| # | Decision | Notes |
| --- | --- | --- |
| 6 | Every Stamp carries a Person name, no auth | [ADR-0004](adr/0004-name-per-stamp-without-auth.md) |
| 7 | Valid transitions enforced per Person; invalid gets HTTP 409, invalid buttons disabled | |
| 8 | Optional Note per Stamp, max 200 characters | Course: "Rapport/Notiz" |
| 9 | Main page: person picker + note + four buttons, Status board, recent Stamps | Selected person remembered in a cookie; "today" is Europe/Zurich |
| 10 | Form POST answers 303 → `/`, JSON POST answers JSON | Same pattern as the instructor's reference app |
| 11 | Storage is SQLite under `/data` | [ADR-0002](adr/0002-sqlite-on-shared-rwo-volume.md) |

## Platform

| # | Decision | Notes |
| --- | --- | --- |
| 12 | k3d single-node cluster | [ADR-0001](adr/0001-k3d-single-node-cluster.md) |
| 13 | Dev: 1 replica, NodePort, imported image, `localhost:8080` | [ADR-0003](adr/0003-dev-local-image-prod-local-registry.md) |
| 14 | Prod: 3 replicas, ClusterIP + Traefik Ingress, local registry, `zeiterfassung.localhost:8081`; actually runs | [ADR-0003](adr/0003-dev-local-image-prod-local-registry.md) |
| 15 | Setup via README (raw commands) plus Makefile shortcuts | |
| 16 | Base image pinned by digest; optional `make scan` with Trivy | |

## Quality

| # | Decision | Notes |
| --- | --- | --- |
| 17 | Unit tests (state machine, validation, escaping, storage) and a cluster smoke test incl. persistence across pod deletion | |
| 18 | `/health` proves the volume is writable, not only that the process answers | |

## Documentation

| # | Decision | Notes |
| --- | --- | --- |
| 19 | Submission doc in English, Typst, compiled to PDF, max 4 pages A4 | |
| 20 | Sections: SOLL, security requirements, healthchecks, deviations and risks | Slide dictates the first three |
| 21 | Written in Yanick's voice, then a grammar pass | |
| 22 | AI Decision Log as a separate file, Claude Code as the AI, four-column format from the HowTo | |
| 23 | Screenshots as commented-out placeholders until recorded | |
| 24 | No video script | |

## Found during the build

Details and evidence in the [AI decision log](ai-decision-log.md).

| # | Decision | Notes |
| --- | --- | --- |
| 25 | Health probe file gets a unique name per call | Readiness and liveness collided, `503` every 10s |
| 26 | `preStop` sleep of 5s | Rollouts dropped 3 of 290 requests without it |
| 27 | pip removed from the runtime image | Only source of HIGH CVEs |
| 28 | Rootless Docker: kubelet feature gate and `k3d image import --mode direct` | Detected by the Makefile |
| 29 | No root initContainer, `fsGroup` is enough on `local-path` | Verified with `ls -la /data` |
| 30 | Image tags are never reused, every change gets a new version (now 1.4) | |

## After the first review

| # | Decision | Notes |
| --- | --- | --- |
| 31 | Name field is a picker of existing Persons; Enter on an unknown name creates the Person | `POST /person`, a small script auto-selects on pick, works without it too |
| 32 | Stamping an unknown name is rejected with `404` | No accidental Persons from typos |
| 33 | Existing databases are migrated: everyone with stamps becomes a Person | Runs at startup, idempotent |
| 34 | Only Docker, k3d, kubectl, make and curl on the host | Unit tests run in a Dockerfile `test` stage, Typst in its container |
| 35 | The compiled PDF is committed | |
