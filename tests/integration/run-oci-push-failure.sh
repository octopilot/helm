#!/usr/bin/env bash
# Integration test: when helm push fails, build fails and push-failed is written (no ref).
# Uses an unreachable registry so push fails without needing auth.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BUILDPACK_TGZ="${ROOT_DIR}/build/buildpack.tgz"
CHART_PATH="${ROOT_DIR}/tests/integration"
OUT_DIR="${ROOT_DIR}/build/oci-push-fail-out"
# Unreachable registry so helm push fails
OCI_REF="localhost:9999/nonexistent/helm-chart"

if [[ ! -f "${BUILDPACK_TGZ}" ]]; then
  echo "Run scripts/package.sh first to create build/buildpack.tgz" >&2
  exit 1
fi

rm -rf "${OUT_DIR}"
mkdir -p "${OUT_DIR}"
chmod 764 "${OUT_DIR}"

echo "Building with BP_HELM_OCI_REF=${OCI_REF} (expect push to fail)..."
set +e
pack build "helm-oci-push-fail-test:latest" \
  --builder paketobuildpacks/builder-jammy-base \
  --buildpack "${BUILDPACK_TGZ}" \
  --path "${CHART_PATH}" \
  --env "BP_HELM_OCI_REF=${OCI_REF}" \
  --env "BP_HELM_OCI_OUTPUT=/out" \
  --env "BP_HELM_OCI_PLAIN_HTTP=true" \
  --volume "${OUT_DIR}:/out" \
  --no-color
PACK_EXIT=$?
set -e

if [[ $PACK_EXIT -eq 0 ]]; then
  echo "FAIL: pack build should have failed when helm push fails" >&2
  exit 1
fi

echo "Verifying no ref file and push-failed present..."
if [[ -f "${OUT_DIR}/ref" ]]; then
  echo "FAIL: ref should not exist when push failed" >&2
  exit 1
fi
if [[ ! -f "${OUT_DIR}/push-failed" ]]; then
  echo "FAIL: push-failed marker should exist when push failed" >&2
  exit 1
fi

echo "OK: build failed as expected, push-failed written, no ref"
