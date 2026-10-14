#!/usr/bin/env bash
# Stamps against a running environment, deletes every pod and checks the stamp
# is still there afterwards. Usage: ./smoke.sh [dev|prod ...] (default: both)
set -euo pipefail

DEV_URL=${DEV_URL:-http://localhost:8080}
PROD_URL=${PROD_URL:-http://zeiterfassung.localhost:8081}

fail() { echo "FAIL: $*" >&2; exit 1; }

stamp() {
  curl -fsS -X POST "$1/stamp" -H 'Content-Type: application/json' \
    -d "{\"name\":\"$2\",\"action\":\"$3\",\"note\":\"smoke test\"}" >/dev/null
}

check_env() {
  local env=$1 url=$2 ns=zeiterfassung-$1
  local person="smoke-$env-$(date +%s)"
  echo "== $env ($url)"

  curl -fsS "$url/health" | grep -q '"healthy"' || fail "$env /health not healthy"
  echo "health ok"

  stamp "$url" "$person" EIN
  curl -fsS "$url/events" | grep -q "$person" || fail "$env stamp not listed"
  echo "stamped EIN as $person"

  local code
  code=$(curl -s -o /dev/null -w '%{http_code}' -X POST "$url/stamp" \
    -H 'Content-Type: application/json' -d "{\"name\":\"$person\",\"action\":\"EIN\"}")
  [[ $code == 409 ]] || fail "$env second EIN returned $code, expected 409"
  echo "second EIN rejected with 409"

  if [[ $env == prod ]]; then
    local pods
    pods=$(for _ in $(seq 20); do curl -fsS "$url/health"; echo; done \
      | sed -n 's/.*"pod":"\([^"]*\)".*/\1/p' | sort -u | wc -l)
    echo "requests answered by $pods different pods"
    (( pods > 1 )) || fail "prod traffic did not spread over replicas"
  fi

  kubectl -n "$ns" delete pod -l app=zeiterfassung --wait=true >/dev/null
  kubectl -n "$ns" rollout status deployment/zeiterfassung --timeout=180s >/dev/null
  for _ in $(seq 30); do
    curl -fsS "$url/health" >/dev/null 2>&1 && break
    sleep 2
  done
  curl -fsS "$url/events" | grep -q "$person" || fail "$env stamp lost after pod restart"
  echo "pods deleted and recreated, stamp still there"

  stamp "$url" "$person" AUS
  echo "$env ok"
}

envs=("$@")
(( ${#envs[@]} )) || envs=(dev prod)
for env in "${envs[@]}"; do
  case $env in
    dev) check_env dev "$DEV_URL" ;;
    prod) check_env prod "$PROD_URL" ;;
    *) fail "unknown environment $env" ;;
  esac
done
