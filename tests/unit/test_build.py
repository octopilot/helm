"""
Unit tests for buildpacks/helm/bin/build (shell script).
Run: pytest tests/unit/test_build.py -v
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

BIN_DIR = Path(__file__).resolve().parent.parent.parent / "bin"
BUILD = BIN_DIR / "build"


def run_build(
    build_dir: Path,
    layers_dir: Path,
    bp_helm_chart_dir: str = "",
    bp_helm_version: str = "3.16.4",
) -> subprocess.CompletedProcess:
    env = {
        **os.environ,
        "CNB_BUILD_DIR": str(build_dir),
        "CNB_LAYERS_DIR": str(layers_dir),
        "BP_HELM_VERSION": bp_helm_version,
    }
    if bp_helm_chart_dir:
        env["BP_HELM_CHART_DIR"] = bp_helm_chart_dir
    return subprocess.run(
        [str(BUILD)],
        env=env,
        capture_output=True,
        text=True,
    )


class TestBuildShell:
    def test_build_packages_chart_at_root(self, tmp_path):
        (tmp_path / "Chart.yaml").write_text("name: unit-test\nversion: 0.1.0\n")
        (tmp_path / "templates").mkdir()
        (tmp_path / "templates" / "NOTES.txt").write_text("test\n")
        layers = tmp_path / "layers"
        layers.mkdir()
        result = run_build(tmp_path, layers)
        assert result.returncode == 0, (result.stdout or "") + (result.stderr or "")
        chart_out = layers / "helm-chart" / "chart"
        versioned_tgz = chart_out / "unit-test-0.1.0.tgz"
        assert versioned_tgz.exists(), f"expected {versioned_tgz}"

    def test_build_packages_chart_under_chart_dir(self, tmp_path):
        chart = tmp_path / "chart"
        chart.mkdir()
        (chart / "Chart.yaml").write_text("name: subchart\nversion: 1.0.0\n")
        (chart / "templates").mkdir()
        (chart / "templates" / "NOTES.txt").write_text("ok\n")
        layers = tmp_path / "layers"
        layers.mkdir()
        result = run_build(tmp_path, layers)
        assert result.returncode == 0, (result.stdout or "") + (result.stderr or "")
        versioned_tgz = layers / "helm-chart" / "chart" / "subchart-1.0.0.tgz"
        assert versioned_tgz.exists(), f"expected {versioned_tgz}"

    def test_build_missing_chart_exits_1(self, tmp_path):
        layers = tmp_path / "layers"
        layers.mkdir()
        result = run_build(tmp_path, layers)
        assert result.returncode == 1
        assert "Chart.yaml" in (result.stderr or "")

    def test_build_missing_name_in_chart_yaml_exits_1(self, tmp_path):
        (tmp_path / "Chart.yaml").write_text("version: 0.1.0\n")
        layers = tmp_path / "layers"
        layers.mkdir()
        result = run_build(tmp_path, layers)
        assert result.returncode == 1
        assert "name" in (result.stderr or "").lower()
