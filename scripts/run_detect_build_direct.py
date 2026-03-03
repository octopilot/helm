#!/usr/bin/env python3
"""
Run detect and build scripts directly (no pack) to isolate helm buildpack behavior.
Bypasses run image: build (and OCI push when BP_HELM_OCI_REF is set) runs on the host.

Usage:
  cd buildpacks/helm
  python scripts/run_detect_build_direct.py [CHART_DIR]
  CHART_DIR defaults to tests/integration-op style chart (chart/ subdir with Chart.yaml).

  To test OCI push (no pack/run image). From outside the cluster use port 5001 (e.g. localhost:5001):
    BP_HELM_OCI_REF=localhost:5001/org/mychart python scripts/run_detect_build_direct.py tests/integration/chartTemplate
  If BP_HELM_OCI_OUTPUT is unset, ref/digest are written to <CHART_DIR>/.helm-oci-out (persists).
  Optional: BP_HELM_OCI_PLAIN_HTTP=1 for HTTP registries; BP_HELM_DOWNLOAD_INSECURE=1 for Helm download behind proxy.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HELM_BIN = Path(__file__).resolve().parent.parent / "bin"
DEFAULT_CHART_DIR = Path(__file__).resolve().parent.parent / "tests" / "integration-op" / "chart"


def run_detect(build_dir: Path) -> int:
    env = os.environ.copy()
    env["CNB_BUILD_DIR"] = str(build_dir)
    proc = subprocess.run(
        [sys.executable, str(HELM_BIN / "detect")],
        env=env,
        cwd=str(HELM_BIN.parent),
    )
    return proc.returncode


def run_build(build_dir: Path, layers_dir: Path, env_extra: dict[str, str] | None = None) -> int:
    env = os.environ.copy()
    env["CNB_BUILD_DIR"] = str(build_dir)
    env["CNB_LAYERS_DIR"] = str(layers_dir)
    if env_extra:
        env.update(env_extra)
    proc = subprocess.run(
        [sys.executable, str(HELM_BIN / "build")],
        env=env,
        cwd=str(HELM_BIN.parent),
    )
    return proc.returncode


def main() -> int:
    if len(sys.argv) > 1:
        chart_dir = Path(sys.argv[1]).resolve()
    else:
        # Fallback: op integration fixture path when run from repo root or buildpacks/helm
        for base in [
            Path(__file__).resolve().parent.parent.parent.parent / "octopilot-pipeline-tools" / "tests" / "integration" / "fixtures" / "helm" / "chart",
            Path(__file__).resolve().parent.parent / "tests" / "integration-op" / "chart",
            DEFAULT_CHART_DIR,
        ]:
            if (base / "Chart.yaml").is_file():
                chart_dir = base
                break
        else:
            print("No chart dir with Chart.yaml found. Pass path: python scripts/run_detect_build_direct.py <CHART_DIR>", file=sys.stderr)
            return 1

    if not (chart_dir / "Chart.yaml").is_file():
        print(f"Chart.yaml not found in {chart_dir}", file=sys.stderr)
        return 1

    print(f"[direct] Running detect with CNB_BUILD_DIR={chart_dir}", flush=True)
    code = run_detect(chart_dir)
    print(f"[direct] detect exit code: {code}", flush=True)
    if code != 0:
        return code

    env_extra = {}
    oci_ref = os.environ.get("BP_HELM_OCI_REF", "").strip()
    if oci_ref:
        oci_out = os.environ.get("BP_HELM_OCI_OUTPUT", "").strip()
        if not oci_out:
            oci_out_dir = chart_dir / ".helm-oci-out"
            oci_out_dir.mkdir(parents=True, exist_ok=True)
            oci_out = str(oci_out_dir)
            print(f"[direct] OCI push enabled: BP_HELM_OCI_REF={oci_ref} BP_HELM_OCI_OUTPUT={oci_out}", flush=True)
        env_extra["BP_HELM_OCI_REF"] = oci_ref
        env_extra["BP_HELM_OCI_OUTPUT"] = oci_out
        v = os.environ.get("BP_HELM_OCI_PLAIN_HTTP", "").strip()
        if v:
            env_extra["BP_HELM_OCI_PLAIN_HTTP"] = v
        v = os.environ.get("BP_HELM_DOWNLOAD_INSECURE", "").strip()
        if v:
            env_extra["BP_HELM_DOWNLOAD_INSECURE"] = v

    with tempfile.TemporaryDirectory(prefix="op-helm-layers-") as layers_dir:
        layers_path = Path(layers_dir)
        print(f"[direct] Running build with CNB_BUILD_DIR={chart_dir} CNB_LAYERS_DIR={layers_path}", flush=True)
        code = run_build(chart_dir, layers_path, env_extra=env_extra)
        print(f"[direct] build exit code: {code}", flush=True)
        if code == 0:
            chart_tgzs = list((layers_path / "helm-chart" / "chart").glob("*.tgz"))
            if chart_tgzs:
                out_dir = chart_dir / ".helm-out"
                out_dir.mkdir(parents=True, exist_ok=True)
                for src in chart_tgzs:
                    dest = out_dir / src.name
                    shutil.copy2(src, dest)
                    print(f"[direct] Chart tgz copied to {dest} (inspect there; temp layers dir is removed on exit)", flush=True)
        return code


if __name__ == "__main__":
    sys.exit(main())
