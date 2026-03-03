"""
Unit tests for buildpacks/helm/bin/build (pure Python build script).
Every exit path in the script must have a matching test (see EXIT_PATHS.md).
Run from repo root: python -m pytest buildpacks/helm/tests/unit/test_build.py -v
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import patch

import pytest

# Import the build module (bin/build is the script; we test its functions)
BUILD_DIR = Path(__file__).resolve().parent.parent.parent / "bin"
if str(BUILD_DIR) not in sys.path:
    sys.path.insert(0, str(BUILD_DIR))


def _load_build_module():
    build_script = BUILD_DIR / "build"
    with open(build_script, encoding="utf-8") as f:
        code = compile(f.read(), str(build_script), "exec")
    ns = {"__name__": "build", "__file__": str(build_script)}
    exec(code, ns)
    return ns


_build_ns = _load_build_module()

resolve_chart_path = _build_ns["resolve_chart_path"]
parse_chart_yaml_field = _build_ns["parse_chart_yaml_field"]
chart_has_dependencies = _build_ns["chart_has_dependencies"]
validate_chart_layout = _build_ns["validate_chart_layout"]
extract_digest_from_push_output = _build_ns["extract_digest_from_push_output"]
package_chart = _build_ns["package_chart"]
oci_push = _build_ns["oci_push"]
get_env = _build_ns["get_env"]
main = _build_ns["main"]
SystemExitWithMessage = _build_ns["SystemExitWithMessage"]


class TestResolveChartPath:
    def test_chart_at_root(self, tmp_path):
        (tmp_path / "Chart.yaml").write_text("name: foo\nversion: 0.1.0\n")
        assert resolve_chart_path(tmp_path, "") == tmp_path

    def test_chart_under_chart_dir(self, tmp_path):
        chart = tmp_path / "chart"
        chart.mkdir()
        (chart / "Chart.yaml").write_text("name: foo\nversion: 0.1.0\n")
        assert resolve_chart_path(tmp_path, "") == chart

    def test_chart_under_chartTemplate(self, tmp_path):
        ct = tmp_path / "chartTemplate"
        ct.mkdir()
        (ct / "Chart.yaml").write_text("name: foo\nversion: 0.1.0\n")
        assert resolve_chart_path(tmp_path, "") == ct

    def test_bp_helm_chart_dir_set(self, tmp_path):
        sub = tmp_path / "chart" / "mychart"
        sub.mkdir(parents=True)
        (sub / "Chart.yaml").write_text("name: foo\nversion: 0.1.0\n")
        assert resolve_chart_path(tmp_path, "chart/mychart") == sub

    def test_not_found_exits(self, tmp_path):
        with pytest.raises(SystemExitWithMessage) as exc_info:
            resolve_chart_path(tmp_path, "")
        assert "Chart.yaml not found" in exc_info.value.message

    def test_bp_helm_chart_dir_invalid_exits(self, tmp_path):
        (tmp_path / "Chart.yaml").write_text("name: foo\nversion: 0.1.0\n")
        with pytest.raises(SystemExitWithMessage) as exc_info:
            resolve_chart_path(tmp_path, "nonexistent")
        assert "Chart.yaml not found" in exc_info.value.message


class TestParseChartYamlField:
    def test_name_and_version(self, tmp_path):
        chart_yaml = tmp_path / "Chart.yaml"
        chart_yaml.write_text("name: cronjob-log-monitor-chart\nversion: 0.1.0\n")
        assert parse_chart_yaml_field(chart_yaml, "name") == "cronjob-log-monitor-chart"
        assert parse_chart_yaml_field(chart_yaml, "version") == "0.1.0"

    def test_trim_quotes_and_whitespace(self, tmp_path):
        chart_yaml = tmp_path / "Chart.yaml"
        chart_yaml.write_text('name: " mychart "\nversion: 1.2.3\n')
        assert parse_chart_yaml_field(chart_yaml, "name") == "mychart"
        assert parse_chart_yaml_field(chart_yaml, "version") == "1.2.3"


class TestChartHasDependencies:
    def test_has_dependencies(self, tmp_path):
        (tmp_path / "Chart.yaml").write_text("name: x\nversion: 0.1.0\ndependencies:\n  - name: y\n")
        assert chart_has_dependencies(tmp_path / "Chart.yaml") is True

    def test_no_dependencies(self, tmp_path):
        (tmp_path / "Chart.yaml").write_text("name: x\nversion: 0.1.0\n")
        assert chart_has_dependencies(tmp_path / "Chart.yaml") is False


class TestValidateChartLayout:
    def test_valid_returns_name_version(self, tmp_path):
        (tmp_path / "Chart.yaml").write_text("name: myapp\nversion: 1.0.0\n")
        name, version = validate_chart_layout(tmp_path)
        assert name == "myapp"
        assert version == "1.0.0"

    def test_missing_name_exits(self, tmp_path):
        (tmp_path / "Chart.yaml").write_text("version: 1.0.0\n")
        with pytest.raises(SystemExitWithMessage) as exc_info:
            validate_chart_layout(tmp_path)
        assert "name:" in exc_info.value.message

    def test_missing_version_exits(self, tmp_path):
        (tmp_path / "Chart.yaml").write_text("name: myapp\n")
        with pytest.raises(SystemExitWithMessage) as exc_info:
            validate_chart_layout(tmp_path)
        assert "version:" in exc_info.value.message

    def test_same_name_subdir_exits(self, tmp_path):
        (tmp_path / "Chart.yaml").write_text("name: myapp\nversion: 1.0.0\n")
        (tmp_path / "myapp").mkdir()
        with pytest.raises(SystemExitWithMessage) as exc_info:
            validate_chart_layout(tmp_path)
        assert "subdirectory named 'myapp'" in exc_info.value.message
        assert "stackoverflow.com" in exc_info.value.extra

    def test_trimmed_name_used_for_check(self, tmp_path):
        (tmp_path / "Chart.yaml").write_text("name:  mychart  \nversion: 0.1.0\n")
        (tmp_path / "mychart").mkdir()
        with pytest.raises(SystemExitWithMessage):
            validate_chart_layout(tmp_path)

    def test_chart_yaml_missing_exits(self, tmp_path):
        """Exit path 3: Chart.yaml not a file at chart_path."""
        # tmp_path exists but has no Chart.yaml
        with pytest.raises(SystemExitWithMessage) as exc_info:
            validate_chart_layout(tmp_path)
        assert "Chart.yaml not found at" in exc_info.value.message
        assert "CHART-LAYOUT" in exc_info.value.extra


class TestPackageChart:
    def test_no_tgz_exits(self, tmp_path):
        """Exit path 10: helm package did not produce a .tgz."""
        chart_path = tmp_path / "chart"
        chart_path.mkdir()
        (chart_path / "Chart.yaml").write_text("name: foo\nversion: 0.1.0\n")
        chart_out_layer = tmp_path / "out"
        helm_bin = tmp_path / "helm"
        helm_bin.mkdir()
        (helm_bin / "helm").write_text("#!/bin/sh\nexit 0")
        (helm_bin / "helm").chmod(0o755)
        # Mock run_helm so package step does not create any .tgz
        def mock_run_helm(helm_bin, args, cwd=None, env=None, capture=False):
            return CompletedProcess(args=[], returncode=0, stdout="", stderr="")
        with patch.dict(_build_ns, {"run_helm": mock_run_helm}):
            with pytest.raises(SystemExitWithMessage) as exc_info:
                _build_ns["package_chart"](Path(helm_bin / "helm"), chart_path, chart_out_layer)
        assert "helm package did not produce a .tgz" in exc_info.value.message
        assert "Check chart layout" in exc_info.value.extra


class TestOciPush:
    def test_helm_push_failure_exits(self, tmp_path):
        """Exit path 11: run_helm(push) returncode != 0."""
        chart_tgz = tmp_path / "chart.tgz"
        chart_tgz.write_bytes(b"x")
        out_dir = tmp_path / "out"
        helm_bin = tmp_path / "helm"
        helm_bin.mkdir()
        (helm_bin / "helm").write_text("x")
        def mock_run_helm(helm_bin, args, cwd=None, env=None, capture=False):
            return CompletedProcess(args=args, returncode=1, stdout="", stderr="push failed")
        with patch.dict(_build_ns, {"run_helm": mock_run_helm}):
            with pytest.raises(SystemExitWithMessage) as exc_info:
                _build_ns["oci_push"](Path(helm_bin / "helm"), chart_tgz, "ttl.sh/foo", out_dir, False)
        assert exc_info.value.message == "helm push failed"
        assert "push failed" in exc_info.value.extra

    def test_digest_missing_exits(self, tmp_path):
        """Exit path 12: digest is None after push."""
        chart_tgz = tmp_path / "chart.tgz"
        chart_tgz.write_bytes(b"x")
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        helm_bin = tmp_path / "helm"
        helm_bin.mkdir()
        (helm_bin / "helm").write_text("x")
        def mock_run_helm(helm_bin, args, cwd=None, env=None, capture=False):
            # push returns 0 but output has no sha256
            if "push" in args:
                return CompletedProcess(args=args, returncode=0, stdout="Done", stderr="")
            # show chart for version
            return CompletedProcess(args=args, returncode=0, stdout="version: 0.1.0\n", stderr="")
        with patch.dict(_build_ns, {"run_helm": mock_run_helm}):
            with pytest.raises(SystemExitWithMessage) as exc_info:
                _build_ns["oci_push"](Path(helm_bin / "helm"), chart_tgz, "ttl.sh/foo", out_dir, False)
        assert "Could not extract digest" in exc_info.value.message
        assert "Done" in exc_info.value.extra

    def test_out_dir_not_dir_after_push_exits(self, tmp_path):
        """Exit path 13: not out_dir.is_dir() after push (defensive check)."""
        chart_tgz = tmp_path / "chart.tgz"
        chart_tgz.write_bytes(b"x")
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        helm_bin = tmp_path / "helm"
        helm_bin.mkdir()
        (helm_bin / "helm").write_text("x")
        def mock_run_helm(helm_bin, args, cwd=None, env=None, capture=False):
            return CompletedProcess(
                args=args, returncode=0, stdout="Pushed sha256:abc123", stderr=""
            )
        real_path_is_dir = Path.is_dir
        call_count = [0]
        def is_dir_false_for_out_dir_after_mkdir(self):
            # First call(s) from out_dir.mkdir(exist_ok=True) must return True so mkdir succeeds.
            # Next call is the explicit "if not out_dir.is_dir()" in oci_push → return False to trigger exit.
            call_count[0] += 1
            if self == out_dir and call_count[0] > 1:
                return False
            return real_path_is_dir(self)
        with patch.dict(_build_ns, {"run_helm": mock_run_helm}):
            with patch.object(Path, "is_dir", is_dir_false_for_out_dir_after_mkdir):
                with pytest.raises(SystemExitWithMessage) as exc_info:
                    _build_ns["oci_push"](Path(helm_bin / "helm"), chart_tgz, "ttl.sh/foo", out_dir, False)
        assert "BP_HELM_OCI_OUTPUT" in exc_info.value.message
        assert "not a writable directory" in exc_info.value.message

    def test_write_oserror_exits(self, tmp_path):
        """Exit path 14: OSError when writing digest/ref/copy."""
        chart_tgz = tmp_path / "chart.tgz"
        chart_tgz.write_bytes(b"x")
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        helm_bin = tmp_path / "helm"
        helm_bin.mkdir()
        (helm_bin / "helm").write_text("x")
        def mock_run_helm(helm_bin, args, cwd=None, env=None, capture=False):
            return CompletedProcess(
                args=args, returncode=0, stdout="Pushed sha256:abc123", stderr=""
            )
        real_write_text = Path.write_text
        def write_text_raises_for_digest(self, *args, **kwargs):
            if self.name == "digest":
                raise OSError(13, "Permission denied")
            return real_write_text(self, *args, **kwargs)
        with patch.dict(_build_ns, {"run_helm": mock_run_helm}):
            with patch.object(Path, "write_text", write_text_raises_for_digest):
                with pytest.raises(SystemExitWithMessage) as exc_info:
                    _build_ns["oci_push"](Path(helm_bin / "helm"), chart_tgz, "ttl.sh/foo", out_dir, False)
        assert "BP_HELM_OCI_OUTPUT" in exc_info.value.message
        assert "not a writable directory" in exc_info.value.message
        assert "Permission denied" in exc_info.value.extra


def _mock_get_env(build_dir: str, layers_dir: str, **overrides):
    def get_env(name: str, default: str = "") -> str:
        if name in overrides:
            return overrides[name]
        if name == "CNB_BUILD_DIR":
            return build_dir
        if name == "CNB_LAYERS_DIR":
            return layers_dir
        return os.environ.get(name, default).strip()
    return get_env


class TestMain:
    def test_build_dir_not_directory_exits(self, tmp_path):
        """Exit path 7: CNB_BUILD_DIR is not a directory."""
        not_a_dir = tmp_path / "nonexistent"
        assert not not_a_dir.exists()
        with patch.dict(_build_ns, {"get_env": _mock_get_env(str(not_a_dir), str(tmp_path / "layers"))}):
            with pytest.raises(SystemExit) as exc_info:
                main()
        assert exc_info.value.code == 1

    def test_chart_yaml_missing_after_resolve_exits(self, tmp_path):
        """Exit path 8: chart_path/Chart.yaml not is_file() after resolve (defensive)."""
        (tmp_path / "Chart.yaml").write_text("name: x\nversion: 0.1.0\n")
        (tmp_path / "subdir").mkdir()
        def resolve_returns_path_without_chart(build_dir, chart_dir_env):
            return tmp_path / "subdir"
        with patch.dict(_build_ns, {"resolve_chart_path": resolve_returns_path_without_chart}):
            with patch.dict(_build_ns, {"get_env": _mock_get_env(str(tmp_path), str(tmp_path / "layers"))}):
                with pytest.raises(SystemExit) as exc_info:
                    main()
        assert exc_info.value.code == 1

    def test_install_helm_failure_exits(self, tmp_path):
        """Exit path 9: install_helm raises OSError/URLError/KeyError."""
        (tmp_path / "Chart.yaml").write_text("name: x\nversion: 0.1.0\n")
        layers = tmp_path / "layers"
        layers.mkdir()
        def install_helm_raises(*args, **kwargs):
            raise OSError(2, "No such file or directory")
        with patch.dict(_build_ns, {"get_env": _mock_get_env(str(tmp_path), str(layers))}):
            with patch.dict(_build_ns, {"install_helm": install_helm_raises}):
                with pytest.raises(SystemExit) as exc_info:
                    main()
        assert exc_info.value.code == 1


class TestExtractDigestFromPushOutput:
    def test_finds_sha256(self):
        out = "Pushed: ttl.sh/abc-chart:0.1.0 sha256:deadbeef1234567890"
        assert extract_digest_from_push_output(out) == "sha256:deadbeef1234567890"

    def test_first_match_wins(self):
        out = "sha256:aaa sha256:bbb"
        assert extract_digest_from_push_output(out) == "sha256:aaa"

    def test_none_when_missing(self):
        assert extract_digest_from_push_output("no digest here") is None
