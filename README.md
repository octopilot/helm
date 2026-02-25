# Octopilot Helm Buildpack

Packages a Helm chart and produces a container image whose contents include the packaged chart (`.tgz`). The image can be pushed to an OCI registry and used as a Helm chart OCI artifact, or the chart can be copied out and pushed with `helm push`.

## Detection

- Passes when `Chart.yaml` is present in the build context root or in a `chart/` subdirectory.
- Optional env: `BP_HELM_CHART_DIR` — subdirectory containing `Chart.yaml` (e.g. `chart`).

## Build

1. Installs Helm (cached in a layer; version via `BP_HELM_VERSION`, default `3.16.4`).
2. Runs `helm dependency build` if `Chart.yaml` declares `dependencies`.
3. Runs `helm package` and places the resulting `.tgz` in a **launch** layer so it is present in the run image.
4. Adds a default process so the image is valid (process keeps the container alive; primary use is the chart artifact).

## Output

- The packaged chart is in the run image under the buildpack’s launch layer, e.g.  
  `/layers/octopilot/helm/helm-chart/chart/<name>-<version>.tgz`
- A symlink `chart.tgz` in the same directory points to the packaged file.
- The image can be pushed to GHCR (or any OCI registry); you can then use `helm install myrelease oci://ghcr.io/org/repo/chart --version <tag>` (Helm 3.8+), or extract the `.tgz` from the image and use `helm push` if needed.

## Stacks

- Compatible with any stack (`id = "*"`).

## License

Apache-2.0.
