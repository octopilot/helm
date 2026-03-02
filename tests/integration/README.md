# Integration test chart

Minimal Helm chart used by the Helm buildpack CI to verify that:

1. The buildpack detects `Chart.yaml` and runs.
2. `helm package` produces a `.tgz` in the launch layer.
3. The built image runs and contains the chart at `/layers/*/helm-chart/chart/*.tgz`.
4. **OCI push path:** When `BP_HELM_OCI_REF` and `BP_HELM_OCI_OUTPUT` are set, `helm push` runs and writes `ref` and `digest` to the output directory (see `run-oci-push.sh`).

## Basic integration (no registry)

```bash
pack build helm-integration-test:latest \
  --builder paketobuildpacks/builder-jammy-base \
  --buildpack build/buildpack.tgz \
  --path tests/integration
```

No dependencies or external registries required.

## OCI push integration test

Requires `build/buildpack.tgz` (run `./scripts/package.sh --version <version>` from repo root first) and [pack](https://github.com/buildpacks/pack).

Uses **ttl.sh** (ephemeral, no auth) so the test can run in CI without secrets.

```bash
./tests/integration/run-oci-push.sh [optional-unique-suffix]
```

Verifies that after a successful build:

- `ref` and `digest` exist in the mounted output dir (`build/oci-push-out/`).
- `ref` contains the expected repo and a `sha256:` digest.

## OCI push failure test

When `helm push` fails (e.g. unreachable registry), the build should fail, no `ref` should be written, and the buildpack should write a `push-failed` marker so the platform can tell "push failed" from "OCI path not used".

```bash
./tests/integration/run-oci-push-failure.sh
```

Requires `build/buildpack.tgz` and pack (same as OCI push test above).
