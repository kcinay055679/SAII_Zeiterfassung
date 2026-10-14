# Dev uses an imported image, prod pulls from a local registry

The deck contrasts "DEV: lokales Image" with "PROD: Registry-Image". Dev gets its image via `k3d image import` (like `minikube image load` in the course). Prod pulls from a registry k3d creates next to the cluster, so the prod overlay is not just rendered but actually runs. Both live in one cluster, in namespaces `zeiterfassung-dev` and `zeiterfassung-prod`.
