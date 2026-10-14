# AI decision log

The service was built with Claude Code (Claude Opus 5.5) instead of Hermes, see [ADR-0005](adr/0005-claude-code-instead-of-hermes.md). The format is the one from the Hermes HowTo: what was decided, what the AI proposed, how we checked it and what came out. We only list entries where we actually ran a check. A proposal we just agreed with doesn't count as reviewed.

## overview

| Decision | AI proposal | Check | Result |
| --- | --- | --- | --- |
| Health check | `/health` writes and deletes `/data/.health-<pod>` | `kubectl get events` on prod showed `503` every 10s and one liveness restart | Unique temp file per call, regression test |
| Storage with 3 replicas | SQLite on the RWO volume, status check + insert in one `BEGIN IMMEDIATE` transaction | 20 parallel `EIN` for one person across 3 replicas | 1x `201`, 19x `409`, spread over all pods |
| Rollouts | No `preStop` hook | Load during `rollout restart` | 3 of 290 requests failed, with `preStop` sleep 0 of 678 |
| Runtime image | `python:3.13-slim` base with pip left in | Trivy scan | 4 HIGH in pip's vendored libs, pip removed, 0 HIGH/CRITICAL |
| Cluster on this host | Plain `k3d cluster create` | k3s server logs | Kubelet fails on rootless Docker, feature gate + `--mode direct` import |
| `/data` permissions | `fsGroup`, initContainer with root `chown` as a fallback | Deployed and looked at `ls -la /data` | `fsGroup` is enough, no root initContainer |
| Forced health failure | `chmod 500 /data` in the pod | Ran it | Not permitted, `/data` is owned by root. Locked the database file instead |

## details

#### health check: same probe file for two probes
The first `/health` wrote `/data/.health-<pod>` and deleted it again. That's fine for one caller, but readiness (every 5s) and liveness (every 10s) hit it at the same moment every 10 seconds. Both threads write the same file, the first one deletes it, the second `unlink` gets `FileNotFoundError` and the endpoint answers `503`.

We found it because `kubectl get events --field-selector reason=Unhealthy` was full of `HTTP probe failed with statuscode: 503` on the prod pods, and one pod got restarted by the liveness probe. All unit tests were green at that point, since none of them called `/health` concurrently.

Fix: `tempfile.NamedTemporaryFile(dir=data_dir)` gives every call its own name. A test with 200 parallel health calls failed before the fix and passes after it. On the redeployed pods there were no `Unhealthy` events and no restarts. This is the entry we'd point to first, the AI wrote a health check whose whole point is to catch real problems, and it produced a false one.

#### storage: three replicas on one ReadWriteOnce volume
The deck asks for 3 replicas in prod and persistence on a PVC. `ReadWriteOnce` with `local-path` only works because the cluster has a single node, so all pods mount the same host directory ([ADR-0001](adr/0001-k3d-single-node-cluster.md)). The original plan was a JSONL file with `flock`. We switched to SQLite, because the transition check ("is this person allowed to stamp `PAUSE` right now") needs read and write atomically, across processes in different pods ([ADR-0002](adr/0002-sqlite-on-shared-rwo-volume.md)).

Check: 20 parallel `POST /stamp` with `EIN` for the same new person against prod. Result: exactly one `201`, nineteen `409`, and the gunicorn logs show the requests spread over all three pods. Also part of the unit tests with 8 threads on one database file.

This only holds while every replica shares one kernel and one local filesystem. On a network volume or with more nodes, SQLite locking isn't reliable anymore, and we'd move to a database pod.

#### rollouts: requests dropped during restart
After `make prod` a few stamps from a script just went missing. With `curl` in a loop during `kubectl rollout restart`, 3 of 290 requests failed (`502` or connection reset). Gunicorn shut down on `SIGTERM` before Traefik had removed the pod from its endpoints.

Fix: `preStop: sleep 5`. Two rollout restarts under the same load afterwards had 678 of 678 requests answered with `200`.

#### runtime image: pip
Trivy reported 4 HIGH findings, all in libraries that pip vendors (`msgpack`, `setuptools`, `urllib3`), once in the base image's pip and once in the venv. The app never calls pip at runtime, so we uninstall it in both stages. The rescan has 0 HIGH and 0 CRITICAL. The base image itself is pinned by digest.

#### cluster: rootless Docker
`k3d cluster create` hung, the server logs had `failed to create kubelet: open /dev/kmsg: operation not permitted`. This host runs Docker rootless, so k3s runs inside a user namespace. The fix is the kubelet feature gate `KubeletInUserNamespace=true`. After that, `k3d image import` failed because its tools container mounts `/var/run/docker.sock`, which doesn't exist on rootless, so we import with `--mode direct`. The Makefile detects rootless and only adds these flags when they're needed.

#### /data permissions: no root initContainer needed
The plan had a root initContainer that runs `chown` as a fallback in case `fsGroup` doesn't apply to `local-path` volumes. We deployed without it first. `ls -la /data` shows `drwxrwsrwx root 10001`, the app user can write, `/health` is green. So no container in the pod runs as root.

#### forced health failure: chmod not permitted
To show that the probe actually catches something, the plan was `chmod 500 /data` inside the pod. That fails with `Operation not permitted`, because `/data` belongs to root and the container runs as `10001` without capabilities. That's the security setup doing its job. Instead we did `chmod 000 /data/zeiterfassung.db` (owned by the app user): `/health` answered `503 unable to open database file`, the pod went to `0/1`, the Service stopped routing to it, and after `chmod 644` it was `1/1` again without a restart.
