"""直接 pytest、IDE 工作目录、显式覆盖与失败运行的报告输出。"""
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def report_project(tmp_path):
    (tmp_path / "conftest.py").write_text((ROOT / "conftest.py").read_text(encoding="utf-8"), encoding="utf-8")
    (tmp_path / "pytest.ini").write_text("[pytest]\nerp_report_html = false\n", encoding="utf-8")
    (tmp_path / "test_example.py").write_text('''
import os
from common.report import step, checkpoint, run_phase

def test_example():
    def process():
        step("打开网页")
        checkpoint("检查结果")
        assert os.getenv("REPORT_TEST_FAIL") != "1", "expected failure"
    run_phase("process", process)
''', encoding="utf-8")
    working_dir = tmp_path / "ide-working-directory"
    working_dir.mkdir()
    return tmp_path, working_dir


def launch(project, *extra, fail=False):
    root, working_dir = project
    env = {**os.environ, "PYTHONPATH": str(ROOT), "PYTHONUTF8": "1", "REPORT_TEST_FAIL": "1" if fail else "0"}
    return subprocess.run(
        [sys.executable, "-m", "pytest", "-c", str(root / "pytest.ini"),
         "--confcutdir", str(root), str(root / "test_example.py"), "-q", "-p", "no:cacheprovider",
         "-o", f"erp_report_dir={root / 'reports'}", *extra], cwd=working_dir, env=env,
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60,
    )


def test_default_report_for_direct_pytest_pass_and_failure(report_project):
    root, _ = report_project
    paths = []
    for fail in (False, True):
        result = launch(report_project, fail=fail)
        assert result.returncode == int(fail), result.stdout + result.stderr
        metadata = json.loads((root / "reports/latest.json").read_text(encoding="utf-8"))
        assert metadata["pytest_exit_status"] == int(fail)
        paths.append(Path(metadata["results"]))
        records = list(paths[-1].glob("*-result.json"))
        assert len(records) == 1
        record = json.loads(records[0].read_text(encoding="utf-8"))
        assert record["status"] == ("failed" if fail else "passed")
        assert [s["name"] for s in record["steps"][0]["steps"]] == ["打开网页", "检查结果"]
        assert metadata["html"] is None and not metadata["html_requested"]
    assert paths[0] != paths[1]
    assert all(path.parent == root / "reports/allure-results" for path in paths)


def test_explicit_alluredir_and_missing_cli_keep_test_failure(report_project):
    root, working_dir = report_project
    result = launch(report_project, "--alluredir=custom-results", "--report-html",
                    "--allure-cli", str(root / "missing-allure.exe"), fail=True)
    assert result.returncode == 1, result.stdout + result.stderr
    metadata = json.loads((root / "reports/latest.json").read_text(encoding="utf-8"))
    assert Path(metadata["results"]) == working_dir / "custom-results"
    assert list(Path(metadata["results"]).glob("*-result.json"))
    assert metadata["report_error"] and metadata["html"] is None
    assert "HTML 未生成" in result.stdout


def test_collect_only_does_not_create_report(report_project):
    root, _ = report_project
    result = launch(report_project, "--collect-only")
    assert result.returncode == 0, result.stdout + result.stderr
    assert not (root / "reports").exists()


def test_step_start_screenshots_attach_to_matching_titles(report_project):
    root, _ = report_project
    (root / "test_example.py").write_text('''
import base64
import pytest
from common.config import Config, Context
from common.report import step, checkpoint, default_title, run_phase

PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII=")

@pytest.mark.parametrize("mode", ["enabled", "disabled", "broken", "no_driver"])
def test_screenshots(mode):
    events = []
    class Driver:
        def execute_script(self, *args):
            return []
        def get_screenshot_as_png(self):
            events.append("screenshot")
            if mode == "broken":
                raise RuntimeError("截图设备不可用")
            return PNG
    context = Context(Config(screenshots=mode != "disabled"),
                      driver=None if mode == "no_driver" else Driver())
    def process():
        step("打开网页")
        default_title("step", "已有标题时不重复截图")
        events.append("action")
        checkpoint("检查结果")
        events.append("check")
    run_phase("process", process, context)
    if mode in {"enabled", "broken"}:
        assert events == ["screenshot", "action", "screenshot", "check"]
    else:
        assert events == ["action", "check"]
''', encoding="utf-8")
    result = launch(report_project)
    assert result.returncode == 0, result.stdout + result.stderr
    metadata = json.loads((root / "reports/latest.json").read_text(encoding="utf-8"))
    results_dir = Path(metadata["results"])
    records = [json.loads(p.read_text(encoding="utf-8")) for p in results_dir.glob("*-result.json")]
    assert len(records) == 4
    for record in records:
        assert record["status"] == "passed"
        mode = next(p["value"].strip("'") for p in record["parameters"] if p["name"] == "mode")
        for node in record["steps"][0]["steps"]:
            attachments = node.get("attachments", [])
            if mode == "enabled":
                assert len(attachments) == 1
                assert attachments[0]["name"] == "步骤开始：" + node["name"]
                assert attachments[0]["type"] == "image/png"
                assert (results_dir / attachments[0]["source"]).read_bytes().startswith(b"\x89PNG")
            else:
                assert not attachments
