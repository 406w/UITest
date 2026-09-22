import os
from uuid import uuid4

import pytest

from common.config import Config, Context, ROOT
from common.driver import DriverFactory
from common.report import capture_failure_safely, run_phase
from common.report_config import (
    add_report_options, pytest_configure, pytest_sessionfinish, pytest_terminal_summary,
)
from common.test_case import TestCase
from data.database import Database
from page.page_objects.locator import initialize_page_registry


def pytest_addoption(parser):
    add_report_options(parser)
    group = parser.getgroup("erp-ui")
    group.addoption("--base-url", default=os.getenv("ERP_BASE_URL", "http://localhost:8090"))
    group.addoption("--browser", choices=["edge", "chrome", "firefox"], default=os.getenv("ERP_BROWSER", "edge"))
    group.addoption("--headed", action="store_true", help="显示浏览器窗口，默认无头模式")
    group.addoption("--ui-timeout", type=float, default=10)
    group.addoption("--driver-path", default=os.getenv("ERP_DRIVER_PATH"))
    group.addoption("--browser-binary", default=os.getenv("ERP_BROWSER_BINARY"))
    group.addoption("--remote-url", default=os.getenv("SELENIUM_REMOTE_URL"), help="Selenium Grid 地址；不传则使用本机浏览器")
    group.addoption("--no-screenshots", action="store_true")
    group.addoption("--click-snapshots", action="store_true")
    group.addoption("--data-file", default=str(ROOT / "data" / "data.yaml"))


@pytest.fixture(scope="session")
def runtime_config(pytestconfig):
    initialize_page_registry()
    return Config(base_url=pytestconfig.getoption("--base-url"), browser=pytestconfig.getoption("--browser"),
                  headless=not pytestconfig.getoption("--headed"), timeout=pytestconfig.getoption("--ui-timeout"),
                  driver_path=pytestconfig.getoption("--driver-path"), browser_binary=pytestconfig.getoption("--browser-binary"),
                  remote_url=pytestconfig.getoption("--remote-url"),
                  screenshots=not pytestconfig.getoption("--no-screenshots"),
                  click_snapshots=pytestconfig.getoption("--click-snapshots"))


@pytest.fixture(scope="session")
def database(pytestconfig):
    # 不使用 pytest 的系统临时目录：IDE/直接 pytest 运行也采用工程内独立副本。
    # 每个会话（包括 xdist worker）使用唯一目录，避免并发覆盖或权限残留。
    db = Database(ROOT / ".runtime" / "ui-data" / uuid4().hex / "db.db")
    try:
        db.initialize(pytestconfig.getoption("--data-file"))
        yield db
    finally:
        db.close()


@pytest.fixture
def context(request, runtime_config):
    ctx = Context(runtime_config, nodeid=request.node.nodeid)
    request.node.ui_context = ctx
    try:
        ctx.driver = DriverFactory.create(runtime_config)
        yield ctx
    finally:
        DriverFactory.close(ctx)


@pytest.fixture(autouse=True)
def case_lifecycle(request):
    case = request.instance
    if not isinstance(case, TestCase):
        yield
        return
    # 先初始化数据存储，避免为无效 YAML 创建浏览器。
    db = request.getfixturevalue("database")
    ctx = request.getfixturevalue("context")
    case.bind_resources(context=ctx, database=db)

    def restore():
        ctx.phase = "teardown"
        run_phase("teardown：环境恢复", case.teardown, ctx)

    request.addfinalizer(restore)
    ctx.phase = "setup"
    run_phase("init：用例初始化", case.init, ctx)
    run_phase("setup：预置步骤", case.setup, ctx)
    ctx.phase = "call"
    yield


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    ctx = getattr(item, "ui_context", None)
    if report.failed and ctx:
        ctx.phase = report.when
        capture_failure_safely(ctx, report.when)
