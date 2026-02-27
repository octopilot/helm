# Integration test chart

Minimal Helm chart used by the Helm buildpack CI to verify that:

1. The buildpack detects `Chart.yaml` and runs.
2. `helm package` produces a `.tgz` in the launch layer.
3. The built image runs and contains the chart at `/layers/*/helm-chart/chart/*.tgz`.

CI runs:

```bash
pack build helm-integration-test:latest \
  --builder paketobuildpacks/builder-jammy-base \
  --buildpack build/buildpack.tgz \
  --path tests/integration
```

No dependencies or external registries required.
