"""pytest 全局配置：driver fixture（多端适配）与失败截图。"""
import allure
import pytest

from common.driver.webdriver_factory import WebDriverFactory


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


@pytest.fixture(scope="function")
def driver(request):
    platform = request.config.getoption("--platform")
    browser = request.config.getoption("--browser")
    driver = WebDriverFactory(platform=platform, browser=browser).create()
    driver.set_page_load_timeout(30)
    yield driver
    driver.quit()


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    if report.when == "call" and report.failed:
        driver = item.funcargs.get("driver")
        if driver:
            try:
                allure.attach(
                    driver.get_screenshot_as_png(),
                    name="failure_screenshot",
                    attachment_type=allure.attachment_type.PNG,
                )
            except Exception:
                pass
