#!/usr/bin/env bash
set -euox pipefail

ROOT_DIR="$(cd "$(dirname "${0}")/.." && pwd)"
BIN_DIR="${ROOT_DIR}/.bin"
BUILD_DIR="${ROOT_DIR}/build"

source "${ROOT_DIR}/scripts/.util/tools.sh"
source "${ROOT_DIR}/scripts/.util/print.sh"

function main {
  local version token=""
  while [[ "${#}" -ne 0 ]]; do
    case "${1}" in
      --version|-v) version="${2}"; shift 2 ;;
      --token|-t) token="${2}"; shift 2 ;;
      --help|-h) usage; exit 0 ;;
      *) util::print::error "unknown argument ${1}" ;;
    esac
  done

  [[ -z "${version:-}" ]] && { usage; util::print::error "--version is required"; }
  repo::prepare
  tools::install "${token}"
  buildpack::archive "${version}"
}

function usage() {
  cat <<'USAGE'
package.sh --version <version> [--token <token>]
  Package the Helm buildpack for distribution.
USAGE
}

function repo::prepare() {
  util::print::title "Preparing repo..."
  rm -rf "${BUILD_DIR}"
  mkdir -p "${BIN_DIR}" "${BUILD_DIR}"
  export PATH="${BIN_DIR}:${PATH}"
}

function tools::install() {
  util::tools::jam::install --directory "${BIN_DIR}" --token "${1}"
  util::tools::pack::install --directory "${BIN_DIR}" --token "${1}"
}

function buildpack::archive() {
  util::print::title "Packaging buildpack into ${BUILD_DIR}/buildpack.tgz..."
  jam pack --buildpack "${ROOT_DIR}/buildpack.toml" --version "${1}" --offline --output "${BUILD_DIR}/buildpack.tgz"
}

main "${@:-}"
