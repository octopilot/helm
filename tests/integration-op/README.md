# Integration test: op + Octopilot builder (chart path)

Layout (chart in named subdirectory): `chart/chartTemplate/` contains `Chart.yaml`, `values.yaml`, `templates/`. Skaffold context is `chart`; the buildpack auto-detects `chartTemplate` as the chart root.

This fixture is used by the **Integration (op + Octopilot builder)** CI job to exercise the real Octopilot pipeline:

- **op** (from octopilot-pipeline-tools) runs `op build --push`
- Builder: **ghcr.io/octopilot/builder-jammy-base** (includes the Helm buildpack)
- Artifact name **helm-op-test-chart** (ends with `-chart`) so op uses the chart path: Publish=false, BP_HELM_OCI_REF, volume `/out`, ref/digest in `build_result.json`
- Push target: **ttl.sh** (ephemeral, no auth) for CI

See [INTEGRATION-OCTOPILOT-ALIGNMENT.md](../../docs/INTEGRATION-OCTOPILOT-ALIGNMENT.md) for why we run this and how it differs from the pack-based integration test.
