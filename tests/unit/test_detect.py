"""
Unit tests for buildpacks/helm/bin/detect (pure Python detect script).
Every exit path must have a matching test (see EXIT_PATHS_DETECT.md).
Run: python -m pytest buildpacks/helm/tests/unit/test_detect.py -v
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

BUILD_BIN_DIR = Path(__file__).resolve().parent.parent.parent / "bin"
if str(BUILD_BIN_DIR) not in sys.path:
    sys.path.insert(0, str(BUILD_BIN_DIR))


def _load_detect_module():
    detect_script = BUILD_BIN_DIR / "detect"
    with open(detect_script, encoding="utf-8") as f:
        code = compile(f.read(), str(detect_script), "exec")
    ns = {"__name__": "detect", "__file__": str(detect_script)}
    exec(code, ns)
    return ns


_detect_ns = _load_detect_module()

detect_chart = _detect_ns["detect_chart"]
get_env = _detect_ns["get_env"]
main = _detect_ns["main"]


class TestDetectChart:
    """Tests for detect_chart() (no exit, just return value)."""

    def test_chart_at_root(self, tmp_path):
        (tmp_path / "Chart.yaml").write_text("name: x\nversion: 0.1.0\n")
        assert detect_chart(tmp_path, "") is True

    def test_chart_under_chart_dir(self, tmp_path):
        (tmp_path / "chart").mkdir()
        (tmp_path / "chart" / "Chart.yaml").write_text("name: x\nversion: 0.1.0\n")
        assert detect_chart(tmp_path, "") is True

    def test_bp_helm_chart_dir_set_found(self, tmp_path):
        (tmp_path / "sub" / "chart").mkdir(parents=True)
        (tmp_path / "sub" / "chart" / "Chart.yaml").write_text("name: x\nversion: 0.1.0\n")
        assert detect_chart(tmp_path, "sub/chart") is True

    def test_not_found_empty_dir(self, tmp_path):
        assert detect_chart(tmp_path, "") is False

    def test_not_found_bp_helm_chart_dir_invalid(self, tmp_path):
        (tmp_path / "Chart.yaml").write_text("name: x\nversion: 0.1.0\n")
        assert detect_chart(tmp_path, "nonexistent") is False

    def test_chartTemplate_not_checked(self, tmp_path):
        """Current detect does not check chartTemplate (same as original shell script)."""
        (tmp_path / "chartTemplate").mkdir()
        (tmp_path / "chartTemplate" / "Chart.yaml").write_text("name: x\nversion: 0.1.0\n")
        assert detect_chart(tmp_path, "") is False


class TestDetectMainExits:
    """Exit path tests: every exit (0 and 100) must be asserted."""

    def test_detect_chart_at_root_exits_0(self, tmp_path):
        """Exit path 1: chart at build root → exit 0."""
        (tmp_path / "Chart.yaml").write_text("name: x\nversion: 0.1.0\n")
        with patch.dict(_detect_ns, {"get_env": lambda n, d="": str(tmp_path) if n == "CNB_BUILD_DIR" else (d or "")}):
            with pytest.raises(SystemExit) as exc_info:
                main()
        assert exc_info.value.code == 0

    def test_detect_chart_under_chart_exits_0(self, tmp_path):
        """Exit path 1: chart under chart/ → exit 0."""
        (tmp_path / "chart").mkdir()
        (tmp_path / "chart" / "Chart.yaml").write_text("name: x\nversion: 0.1.0\n")
        with patch.dict(_detect_ns, {"get_env": lambda n, d="": str(tmp_path) if n == "CNB_BUILD_DIR" else (d or "")}):
            with pytest.raises(SystemExit) as exc_info:
                main()
        assert exc_info.value.code == 0

    def test_detect_bp_helm_chart_dir_set_exits_0(self, tmp_path):
        """Exit path 1: BP_HELM_CHART_DIR set and Chart.yaml there → exit 0."""
        (tmp_path / "chart" / "mychart").mkdir(parents=True)
        (tmp_path / "chart" / "mychart" / "Chart.yaml").write_text("name: x\nversion: 0.1.0\n")

        def mock_get_env(name: str, default: str = "") -> str:
            if name == "CNB_BUILD_DIR":
                return str(tmp_path)
            if name == "BP_HELM_CHART_DIR":
                return "chart/mychart"
            return os.environ.get(name, default).strip()

        with patch.dict(_detect_ns, {"get_env": mock_get_env}):
            with pytest.raises(SystemExit) as exc_info:
                main()
        assert exc_info.value.code == 0

    def test_detect_not_found_exits_100(self, tmp_path):
        """Exit path 2: no Chart.yaml in root or chart/ → exit 100."""
        with patch.dict(_detect_ns, {"get_env": lambda n, d="": str(tmp_path) if n == "CNB_BUILD_DIR" else (d or "")}):
            with pytest.raises(SystemExit) as exc_info:
                main()
        assert exc_info.value.code == 100

    def test_detect_bp_helm_chart_dir_invalid_exits_100(self, tmp_path):
        """Exit path 2: BP_HELM_CHART_DIR set but path has no Chart.yaml → exit 100."""
        (tmp_path / "Chart.yaml").write_text("name: x\nversion: 0.1.0\n")

        def mock_get_env(name: str, default: str = "") -> str:
            if name == "CNB_BUILD_DIR":
                return str(tmp_path)
            if name == "BP_HELM_CHART_DIR":
                return "nonexistent"
            return os.environ.get(name, default).strip()

        with patch.dict(_detect_ns, {"get_env": mock_get_env}):
            with pytest.raises(SystemExit) as exc_info:
                main()
        assert exc_info.value.code == 100
