"""框架边界验证，不启动浏览器或修改 ERP。"""
import json
import os
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

import pytest

from common.elements import AmbiguousElement, MissingResolver, parse_declaration, resolve_declared_element, xpath_literal
from common.report import ReportUsageError, checkpoint, step
from data.database import Database
from page.page_objects.locator import ways_to

ROOT = Path(__file__).resolve().parents[1]


class FakeElement:
    tag_name = "button"
    text = "登录"

    def __init__(self, element_type="button"):
        self.element_type = element_type

    def get_dom_attribute(self, key):
        return {"id": "43656", "type": self.element_type}.get(key)


class FakeRoot:
    def __init__(self, elements):
        self.elements = elements

    def find_elements(self, by, selector):
        return self.elements


def test_pe_combines_all_conditions_and_rejects_ambiguity():
    class Login:
        id = "43656"
        type = "button"
        text = "登录"

    good, bad = FakeElement(), FakeElement("submit")
    assert resolve_declared_element(FakeRoot([bad, good]), Login) is good
    with pytest.raises(AmbiguousElement):
        resolve_declared_element(FakeRoot([good, good]), Login)


def test_declarations_validate_extension_fields():
    class DescriptionOnly:
        """由 PO 实现"""
    with pytest.raises(MissingResolver):
        parse_declaration(DescriptionOnly)
    for fields in ({"naem": "username"}, {"css": "button", "xpath": "//button"},
                   {"id": "one", "attrs": {"id": "two"}}):
        with pytest.raises(ValueError):
            parse_declaration(type("Invalid", (), fields))
    assert xpath_literal('a\'b"c') == 'concat(\'a\', "\'", \'b"c\')'


def test_route_registry_is_complete_before_browser_creation():
    assert {(r.source, r.action) for r in ways_to("login")} == {("home", "logout")}
    assert {(r.source, r.action) for r in ways_to("home")} == {("login", "submit_success")}
    assert len(ways_to("sale", source="home")) == 1


def test_database_idempotent_and_credentials_not_persisted(tmp_path, monkeypatch):
    db = Database(tmp_path / "db.db")
    try:
        db.initialize(ROOT / "data/data.yaml")
        db.initialize(ROOT / "data/data.yaml")
        assert db.connection.execute("SELECT COUNT(*) FROM test_data").fetchone()[0] == 3
        monkeypatch.setenv("ERP_TEST_PASSWORD", "private-test-secret")
        account = db.account("admin")
        assert account.password == "private-test-secret"
        assert account.password not in repr(account)
        assert account.password not in str(db.connection.execute("SELECT payload FROM test_data").fetchall())
        original = db.get("accounts", "admin")
        with pytest.raises(ValueError):
            db.save_account({**original, "password": "must-not-save"})
        assert db.get("accounts", "admin") == original
        assert db.get("orders", "sale")["type"] == "sale"
        with pytest.raises(KeyError):
            db.get("accounts", "' OR 1=1 --")
    finally:
        db.close()


def test_title_outside_lifecycle_rejected():
    with pytest.raises(ReportUsageError):
        step("孤立步骤")
    with pytest.raises(ReportUsageError):
        checkpoint("孤立检查点")


def test_real_pytest_lifecycle_and_allure_failure_attribution(tmp_path):
    """真实 pytest 子进程验证：初始化/前置失败清理、双重失败及标题状态。"""
    overrides = '''
from pathlib import Path
@pytest.fixture(scope="session")
def database():
    return object()
@pytest.fixture
def context(request):
    ctx = Context(Config(screenshots=False), nodeid=request.node.nodeid)
    request.node.ui_context = ctx
    yield ctx
'''
    (tmp_path / "conftest.py").write_text((ROOT / "conftest.py").read_text(encoding="utf-8") + overrides, encoding="utf-8")
    (tmp_path / "test_cases.py").write_text('''
from pathlib import Path
from common.test_case import TestCase
from common.report import step, checkpoint

def event(name):
    with Path("events.txt").open("a", encoding="utf-8") as out:
        out.write(name + "\\n")

class TestSuccess(TestCase):
    __test__ = True
    def init(self): event("success.init")
    def setup(self): event("success.setup")
    def process(self):
        step("打开网页")
        event("success.process")
        checkpoint("页面正确")
        assert True
    def teardown(self): event("success.teardown")

class TestInitFailure(TestCase):
    __test__ = True
    def init(self):
        event("init.init")
        raise ValueError("init failed")
    def setup(self): event("SHOULD_NOT_RUN")
    def process(self): event("SHOULD_NOT_RUN")
    def teardown(self): event("init.teardown")

class TestSetupFailure(TestCase):
    __test__ = True
    def setup(self):
        event("setup.setup")
        raise ValueError("setup failed")
    def process(self): event("SHOULD_NOT_RUN")
    def teardown(self): event("setup.teardown")

class TestDoubleFailure(TestCase):
    __test__ = True
    def process(self):
        step("已完成操作")
        checkpoint("失败检查点")
        assert False, "original assertion"
        step("SHOULD_NOT_RUN")
    def teardown(self):
        event("double.teardown")
        step("恢复失败")
        raise RuntimeError("cleanup failed")
''', encoding="utf-8")
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT)
    run = subprocess.run([sys.executable, "-m", "pytest", "--confcutdir", str(tmp_path),
                          "test_cases.py", "-q", "--alluredir=results", "--no-report-html",
                          "--junitxml=outcomes.xml", "-p", "no:cacheprovider",
                          "-o", f"erp_report_dir={tmp_path / 'reports'}"], cwd=tmp_path,
                         env=env, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
    assert run.returncode == 1, run.stdout + run.stderr
    outcomes = ET.parse(tmp_path / "outcomes.xml").getroot()
    assert len(outcomes.findall(".//failure")) == 1, run.stdout
    assert len(outcomes.findall(".//error")) == 3, run.stdout
    assert len([case for case in outcomes.findall(".//testcase")
                if case.find("failure") is None and case.find("error") is None]) == 1, run.stdout
    events = (tmp_path / "events.txt").read_text(encoding="utf-8").splitlines()
    assert events[:4] == ["success.init", "success.setup", "success.process", "success.teardown"]
    assert "init.teardown" in events and "setup.teardown" in events and "double.teardown" in events
    assert "SHOULD_NOT_RUN" not in events
    results = [json.loads(p.read_text(encoding="utf-8")) for p in (tmp_path / "results").glob("*-result.json")]
    passed = next(r for r in results if "TestSuccess" in r["fullName"])
    assert [s["name"] for s in passed["steps"][0]["steps"]] == ["打开网页", "页面正确"]
    assert all(s["status"] == "passed" for s in passed["steps"][0]["steps"])
    failed = next(r for r in results if "TestDoubleFailure" in r["fullName"])
    phase = failed["steps"][0]
    assert [s["status"] for s in phase["steps"]] == ["passed", "failed"]
    assert "original assertion" in phase["steps"][1]["statusDetails"]["message"]
    assert "cleanup failed" in run.stdout
