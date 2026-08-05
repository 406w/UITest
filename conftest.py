"""pytest 全局配置：driver fixture（多端适配）与失败截图。"""
from pathlib import Path

import allure
import pytest

from common.driver import DriverManager

PROJECT_ROOT = Path(__file__).resolve().parent
ALLURE_RESULTS_DIR = PROJECT_ROOT / "report" / "allure-results"


def pytest_configure(config):
    ALLURE_RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    config.option.allure_report_dir = str(ALLURE_RESULTS_DIR)
    config.option.clean_alluredir = True


def pytest_addoption(parser):
    parser.addoption(
        "--platform",
        action="store",
        default="web",
        choices=["web", "android", "ios"],
        help="被测平台: web / android / ios（默认 web，仅验证 web 端）",
    )
    parser.addoption(
        "--browser",
        action="store",
        default="edge",
        choices=["edge", "chrome", "firefox"],
        help="web 端浏览器（默认 edge）",
    )
    parser.addoption(
        "--headless",
        action="store_true",
        default=False,
        help="web 端浏览器无头模式（CI/Docker 环境使用）",
    )


@pytest.fixture(scope="function")
def driver_manager():
    """多设备驱动管理：一个用例可创建多个 driver（多个 web 页面 / 移动设备），用例结束自动全部关闭。"""
    manager = DriverManager()
    yield manager
    manager.close_all()


@pytest.fixture(scope="function")
def driver(request, driver_manager):
    """主 driver：由 DriverManager 统一管理，平台/浏览器由命令行参数决定。"""
    platform = request.config.getoption("--platform")
    browser = request.config.getoption("--browser")
    return driver_manager.create_driver(
        "main",
        platform=platform,
        browser=browser,
        headless=request.config.getoption("--headless"),
    )


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    if report.when == "call" and report.failed:
        driver = item.funcargs.get("driver")
        if driver is None:
            manager = item.funcargs.get("driver_manager")
            if manager and manager.drivers:
                driver = next(iter(manager.drivers.values()))
        if driver:
            try:
                allure.attach(
                    driver.get_screenshot_as_png(),
                    name="failure_screenshot",
                    attachment_type=allure.attachment_type.PNG,
                )
            except Exception:
                pass
