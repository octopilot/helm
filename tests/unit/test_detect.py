"""
Unit tests for buildpacks/helm/bin/detect (shell script).
Run: pytest tests/unit/test_detect.py -v
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

BIN_DIR = Path(__file__).resolve().parent.parent.parent / "bin"
DETECT = BIN_DIR / "detect"


def run_detect(build_dir: Path, bp_helm_chart_dir: str = "") -> int:
    env = {**os.environ, "CNB_BUILD_DIR": str(build_dir)}
    if bp_helm_chart_dir:
        env["BP_HELM_CHART_DIR"] = bp_helm_chart_dir
    result = subprocess.run(
        [str(DETECT)],
        env=env,
        cwd=str(build_dir),
        capture_output=True,
    )
    return result.returncode


class TestDetectShell:
    def test_chart_at_root_exits_0(self, tmp_path):
        (tmp_path / "Chart.yaml").write_text("name: x\nversion: 0.1.0\n")
        assert run_detect(tmp_path) == 0

    def test_chart_under_chart_dir_exits_0(self, tmp_path):
        (tmp_path / "chart").mkdir()
        (tmp_path / "chart" / "Chart.yaml").write_text("name: x\nversion: 0.1.0\n")
        assert run_detect(tmp_path) == 0

    def test_bp_helm_chart_dir_set_found_exits_0(self, tmp_path):
        (tmp_path / "sub" / "chart").mkdir(parents=True)
        (tmp_path / "sub" / "chart" / "Chart.yaml").write_text("name: x\nversion: 0.1.0\n")
        assert run_detect(tmp_path, "sub/chart") == 0

    def test_not_found_exits_100(self, tmp_path):
        assert run_detect(tmp_path) == 100

    def test_bp_helm_chart_dir_invalid_exits_100(self, tmp_path):
        (tmp_path / "Chart.yaml").write_text("name: x\nversion: 0.1.0\n")
        assert run_detect(tmp_path, "nonexistent") == 100
