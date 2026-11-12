# deploy

Everything that runs in the cluster, as code. Argo CD on LM2 reads this folder from Git; nobody applies prod by hand.

App and infrastructure share one repo ([ADR-0007](https://github.com/kcinay055679/HF_SAII_f-ju-gothe/blob/main/spec/adr/0007-app-and-iac-in-one-repo.md)). The split is by path: CI only reacts to `app/`, Argo CD only to `deploy/`.

| Folder | What | Status |
| --- | --- | --- |
| `zeiterfassung/` | the app: Kustomize base with `dev` and `prod` overlays (Deployment, Service, PVC, Ingress). Later also PostgreSQL, NetworkPolicies, RBAC | exists |
| `argocd/` | Argo CD install (Helm values or pinned manifests), the AppProject and one Application per folder here (app of apps) | planned |
| `monitoring/` | kube-prometheus-stack values (Prometheus, Grafana, Alertmanager), ServiceMonitor, PrometheusRules with runbook links, Grafana dashboards as JSON, Alertmanager → Mattermost receiver | planned |
| `logging/` | Loki or ELK values, log shipper | planned |
| `policies/` | Kyverno policies (no `latest`, no privileged, resources required) | planned |
| `backup/` | CronJob with `pg_dump`, restore instructions | planned |

Secrets (database password, Mattermost webhook URL) are never committed in plain text. How they get into the cluster (Sealed Secrets, SOPS or created by hand) is still open.

CI lives in `.github/workflows/` at the repo root, because GitHub only reads it there.
