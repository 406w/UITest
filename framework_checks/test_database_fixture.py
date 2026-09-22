"""直接 pytest/IDE 启动不依赖系统临时目录的回归验证。"""
import os
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]


def test_database_fixture_avoids_system_temp_and_isolates_sessions(tmp_path):
    # 子进程加载真实 fixture，并用权限异常模拟用户机器上不可访问的系统临时目录。
    conftest = (ROOT / "conftest.py").read_text(encoding="utf-8")
    conftest += '''
@pytest.fixture(scope="session")
def tmp_path_factory():
    raise PermissionError("模拟无法访问系统 pytest 临时目录")
'''
    (tmp_path / "conftest.py").write_text(conftest, encoding="utf-8")
    test_file = tmp_path / "test_database.py"
    test_file.write_text('''
from pathlib import Path
import pytest
from common.config import ROOT

def test_database(database):
    assert database.path.is_relative_to(ROOT / ".runtime" / "ui-data")
    assert database.get("orders", "sale")["type"] == "sale"
    with pytest.raises(KeyError):
        database.get("accounts", "session_probe")
    database.save_account({"key": "session_probe", "username": "probe",
        "password_env": "PROBE_PASSWORD", "expected_display_name": "probe"})
    Path(__file__).with_suffix(".path").write_text(str(database.path), encoding="utf-8")
''', encoding="utf-8")
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT)
    env["PYTHONUTF8"] = "1"
    # 从不同于工程根目录的位置启动，模拟 IDE 指定 working directory。
    working_dir = tmp_path / "ide-working-directory"
    working_dir.mkdir()
    paths = []
    for _ in range(2):
        result = subprocess.run(
            [sys.executable, "-m", "pytest", str(test_file), "--confcutdir", str(tmp_path),
             "-q", "-p", "no:cacheprovider", "--no-report-html",
             "-o", f"erp_report_dir={tmp_path / 'reports'}"],
            cwd=working_dir, env=env, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=60,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        paths.append(Path(test_file.with_suffix(".path").read_text(encoding="utf-8")))
    assert paths[0] != paths[1]
    assert all(path.is_file() for path in paths)
