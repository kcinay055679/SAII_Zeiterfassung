# k3d single-node cluster instead of minikube

The course material uses minikube throughout; we run k3d (k3s in Docker) with `--agents 0`. k3s' default StorageClass `local-path` is node-local and the data PVC is `ReadWriteOnce`, so all prod replicas must land on the same node to mount it. A single node guarantees that. Every minikube command has a k3d equivalent listed in the README (`minikube image load` → `k3d image import`, `minikube service` → k3d port mapping).

## Consequences

- No node-failure resilience. Three replicas protect against pod crashes, not node loss.
- Adding agent nodes later breaks prod mounting unless storage changes to an RWX class.
