CLUSTER      ?= saii
REGISTRY     ?= registry.localhost
REGISTRY_PORT ?= 5050
VERSION      ?= 1.2
IMAGE        := zeiterfassung:$(VERSION)
PROD_IMAGE   := localhost:$(REGISTRY_PORT)/zeiterfassung:$(VERSION)
DEV_URL      ?= http://localhost:8080
PROD_URL     ?= http://zeiterfassung.localhost:8081
VENV         := .venv

# Rootless Docker runs k3s in a user namespace where the kubelet can't open
# /dev/kmsg; this feature gate makes it tolerate that.
ROOTLESS := $(shell docker info --format '{{.SecurityOptions}}' 2>/dev/null | grep -q rootless && echo yes)
DOCKER_SOCK := $(patsubst unix://%,%,$(shell docker context inspect --format '{{.Endpoints.docker.Host}}' 2>/dev/null))
K3S_ARGS := $(if $(ROOTLESS),--k3s-arg "--kubelet-arg=feature-gates=KubeletInUserNamespace=true@server:*")

.PHONY: help venv test cluster build dev prod status smoke scan clean

help:
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-10s %s\n", $$1, $$2}'

$(VENV):
	python3 -m venv $(VENV)
	$(VENV)/bin/pip install -q -r app/requirements.txt -r app/requirements-dev.txt

venv: $(VENV) ## Create the local Python environment

test: $(VENV) ## Run the unit tests
	cd app && ../$(VENV)/bin/python -m pytest -q

cluster: ## Create the k3d registry and single-node cluster
	k3d registry list | grep -q k3d-$(REGISTRY) || \
		k3d registry create $(REGISTRY) --port $(REGISTRY_PORT)
	k3d cluster list | grep -q '^$(CLUSTER) ' || \
		k3d cluster create $(CLUSTER) --agents 0 \
			--registry-use k3d-$(REGISTRY):$(REGISTRY_PORT) \
			--port "8080:30080@loadbalancer" \
			--port "8081:80@loadbalancer" \
			$(K3S_ARGS) --wait --timeout 180s
	kubectl config use-context k3d-$(CLUSTER)
	kubectl wait --for=condition=Ready node --all --timeout=120s

build: ## Build the image
	docker build -t $(IMAGE) --build-arg APP_VERSION=$(VERSION) app

dev: build ## Import the image and deploy the dev overlay
	k3d image import $(IMAGE) -c $(CLUSTER) --mode direct
	kubectl apply -k k8s/overlays/dev
	kubectl -n zeiterfassung-dev rollout status deployment/zeiterfassung --timeout=120s

prod: build ## Push the image to the registry and deploy the prod overlay
	docker tag $(IMAGE) $(PROD_IMAGE)
	docker push $(PROD_IMAGE)
	kubectl apply -k k8s/overlays/prod
	kubectl -n zeiterfassung-prod rollout status deployment/zeiterfassung --timeout=180s

status: ## Show pods, services, PVCs and ingress of both environments
	kubectl get pods,svc,pvc,ingress -n zeiterfassung-dev -o wide
	kubectl get pods,svc,pvc,ingress -n zeiterfassung-prod -o wide

smoke: ## Stamp against dev and prod, delete pods, check the data survived
	DEV_URL=$(DEV_URL) PROD_URL=$(PROD_URL) ./smoke.sh

scan: ## Scan the image for known CVEs with Trivy (runs as a container)
	docker run --rm -v $(DOCKER_SOCK):/var/run/docker.sock \
		-v trivy-cache:/root/.cache aquasec/trivy:0.69.3 \
		image --severity HIGH,CRITICAL --ignore-unfixed $(IMAGE)

clean: ## Delete the cluster and the registry, including all data
	k3d cluster delete $(CLUSTER)
	k3d registry delete k3d-$(REGISTRY)
