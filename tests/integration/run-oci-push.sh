#!/usr/bin/env bash
# Integration test for the OCI push path: BP_HELM_OCI_REF + BP_HELM_OCI_OUTPUT.
# Verifies that after a successful build, ref and digest exist and ref contains sha256:.
# Uses ttl.sh (ephemeral, no auth) so CI can run without secrets.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BUILDPACK_TGZ="${ROOT_DIR}/build/buildpack.tgz"
CHART_PATH="${ROOT_DIR}/tests/integration"
OUT_DIR="${ROOT_DIR}/build/oci-push-out"
UNIQUE="${1:-$(date +%s)}"
OCI_REF="ttl.sh/${UNIQUE}-helm-chart"

if [[ ! -f "${BUILDPACK_TGZ}" ]]; then
  echo "Run scripts/package.sh first to create build/buildpack.tgz" >&2
  exit 1
fi

rm -rf "${OUT_DIR}"
mkdir -p "${OUT_DIR}"

echo "Building with BP_HELM_OCI_REF=${OCI_REF} and BP_HELM_OCI_OUTPUT=/out (volume ${OUT_DIR})..."
pack build "helm-oci-push-test:latest" \
  --builder paketobuildpacks/builder-jammy-base \
  --buildpack "${BUILDPACK_TGZ}" \
  --path "${CHART_PATH}" \
  --env "BP_HELM_OCI_REF=${OCI_REF}" \
  --env "BP_HELM_OCI_OUTPUT=/out" \
  --volume "${OUT_DIR}:/out" \
  --no-color

echo "Verifying ref and digest files..."
if [[ ! -f "${OUT_DIR}/ref" ]]; then
  echo "FAIL: ${OUT_DIR}/ref not found" >&2
  exit 1
fi
if [[ ! -f "${OUT_DIR}/digest" ]]; then
  echo "FAIL: ${OUT_DIR}/digest not found" >&2
  exit 1
fi

REF_CONTENT="$(cat "${OUT_DIR}/ref")"
if [[ "${REF_CONTENT}" != *"sha256:"* ]]; then
  echo "FAIL: ref does not contain sha256: digest: ${REF_CONTENT}" >&2
  exit 1
fi
if [[ "${REF_CONTENT}" != *"${OCI_REF}"* ]]; then
  echo "FAIL: ref does not contain expected repo ${OCI_REF}: ${REF_CONTENT}" >&2
  exit 1
fi

DIGEST_CONTENT="$(cat "${OUT_DIR}/digest")"
if [[ "${DIGEST_CONTENT}" != sha256:* ]]; then
  echo "FAIL: digest does not start with sha256:: ${DIGEST_CONTENT}" >&2
  exit 1
fi

echo "OK: ref and digest present and valid (ref=${REF_CONTENT})"
