# Octopilot Helm Buildpack

Packages a Helm chart and produces a container image whose contents include the packaged chart (`.tgz`).

**Helm OCI chart for Flux / `helm install oci://`:** Pushing the **run image** (the container image from Pack) to a registry does **not** produce a Helm OCI chart. It produces a container image with generic OCI layers. Flux OCIRepository and `helm install oci://` require an artifact with layer media type `application/vnd.cncf.helm.chart.content.v1.tar+gzip`, which only **`helm push`** produces. When the platform sets `BP_HELM_OCI_REF`, this buildpack runs `helm push` during build and writes the chart ref/digest to `BP_HELM_OCI_OUTPUT`; that path is the one that produces a proper Helm OCI artifact for Flux and Helm OCI.

## Detection

- Passes when `Chart.yaml` is present in the build context root or in a `chart/` subdirectory.
- Optional env: `BP_HELM_CHART_DIR` — subdirectory containing `Chart.yaml` (e.g. `chart`).

## Build

1. Installs Helm (cached in a layer; version via `BP_HELM_VERSION`, default `3.16.4`).
2. Runs `helm dependency build` if `Chart.yaml` declares `dependencies`.
3. Runs `helm package` and places the resulting `.tgz` in a **launch** layer so it is present in the run image.
4. Adds a default process so the image is valid (process keeps the container alive; primary use is the chart artifact).
5. If `BP_HELM_OCI_REF` is set: runs `helm push` to push the chart as a Helm OCI artifact and writes ref/digest to `BP_HELM_OCI_OUTPUT` (see [OCI output contract](docs/OCI-OUTPUT-CONTRACT.md)).

## Output

- The packaged chart is in the run image under the buildpack’s launch layer, e.g.  
  `/layers/octopilot_helm/helm-chart/chart/<name>-<version>.tgz`
- A symlink `chart.tgz` in the same directory points to the packaged file.
- When `BP_HELM_OCI_REF` and `BP_HELM_OCI_OUTPUT` are set and `helm push` succeeds, the platform reads the chart ref and digest from the output directory (see [OCI output contract](docs/OCI-OUTPUT-CONTRACT.md)).

## Environment variables (OCI push path)

The platform (e.g. op) sets these when it wants a Helm OCI chart pushed during build and the ref/digest written for later use (e.g. Flux OCIRepository, build_result.json).

| Variable | Purpose | Format / notes |
|----------|---------|----------------|
| `BP_HELM_OCI_REF` | OCI repository reference (no tag). The buildpack runs `helm push ... oci://${BP_HELM_OCI_REF}`; Helm tags the pushed chart with the chart version (e.g. `0.1.0`). | e.g. `ttl.sh/my-uuid-chart`, `ghcr.io/org/repo-chart`, `localhost:5001/org/repo-chart` |
| `BP_HELM_OCI_OUTPUT` | Directory where the buildpack writes `ref`, `digest`, and optionally `chart.tgz` after a successful push. Defaults to `/out` if unset. The platform typically mounts a host directory here (e.g. `--volume /host/dir:/out`). | Absolute path, e.g. `/out` |
| `BP_HELM_OCI_PLAIN_HTTP` | When set to a non-empty value other than `0` or `false`, the buildpack passes `--plain-http` to `helm push`. **Required for HTTP/insecure registries** (e.g. local registry at `localhost:5001`). The platform should set this when the registry is in its insecure list. | e.g. `true`, `1` |

See [OCI output contract](docs/OCI-OUTPUT-CONTRACT.md) for the exact files written and behaviour on failure.

## Stacks

- Compatible with any stack (`id = "*"`).

## License

Apache-2.0.
