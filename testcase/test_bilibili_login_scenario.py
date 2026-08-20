"""测试用例层：哔哩哔哩登录场景。

场景：打开 Edge -> 进入哔哩哔哩首页 -> 进入登录页 -> 按指定账号从 data 获取密码并输入。
用例只调用业务流程层（common/business_flow.py）提供的方法，不直接接触 PO 链式细节。
仅验证 web 端。
"""
# ---------------- 引入资源文件 ----------------
import os

import allure
import pytest

from common.base_test_case import TestCaseBase
from common.business_flow import BilibiliLoginFlow
from page.page_elements.bilibili_home_page import BilibiliHomePage

ACCOUNT_USERNAME = os.environ.get("BILI_USERNAME")


class TestBilibiliLoginScenario(TestCaseBase):
    """哔哩哔哩登录场景用例。

    init -> 实例化业务流对象
    setup -> 预置条件：取账号、打开首页、确认未登录
    test_step -> 测试步骤：进入登录页，输入账号密码
    teardown -> 恢复环境：回到首页
    """

    __test__ = False  # 非 pytest 测试类，由下方函数入口调用 run()

    # ---------------- init：初始化测试用例 ----------------
    def _init_objects(self) -> None:
        """引入资源文件并实例化业务流对象。"""
        self.flow = BilibiliLoginFlow(self.driver, platform=self.platform)

    # ---------------- setup：预置条件 ----------------
    def setup(self) -> None:
        with allure.step("预置条件：从 data 获取指定账号"):
            self.account = self.flow.get_account(ACCOUNT_USERNAME)
        self.flow.open_home().ensure_not_logged_in()

    # ---------------- test_step：测试步骤 ----------------
    def test_step(self) -> None:
        with allure.step("执行登录场景：进入登录页并输入账号密码（不提交）"):
            self.flow.go_to_login_page().fill_login_form(
                self.account["username"], self.account["password"]
            )
            self.flow.login.attach_text(
                f"账号: {self.account['username']}\n密码: {self.account['password']}",
                name="login_credentials",
            )
            print(f"\n已输入账号 {self.account['username']} 与密码，场景结束")

    # ---------------- teardown：恢复环境 ----------------
    def teardown(self) -> None:
        """恢复环境：无论执行成败均回到首页初始状态。"""
        with allure.step("恢复环境：回到首页"):
            try:
                self.driver.get(BilibiliHomePage.url)
                self.flow.home.wait_loaded(timeout=10)
            except Exception:
                pass


class TestBilibiliCompleteLoginFlow(TestCaseBase):
    """哔哩哔哩完整登录流程用例：直接调用业务流的 login() 完整流程。"""

    __test__ = False  # 非 pytest 测试类，由下方函数入口调用 run()

    # ---------------- init：初始化测试用例 ----------------
    def _init_objects(self) -> None:
        """引入资源文件并实例化业务流对象。"""
        self.flow = BilibiliLoginFlow(self.driver, platform=self.platform)

    # ---------------- setup：预置条件 ----------------
    def setup(self) -> None:
        with allure.step("预置条件：从 data 获取指定账号"):
            self.account = self.flow.get_account(ACCOUNT_USERNAME)

    # ---------------- test_step：测试步骤 ----------------
    def test_step(self) -> None:
        with allure.step("执行完整登录流程"):
            self.flow.complete_login(self.account["username"], self.account["password"])
            status = self.flow.home.login_status()
            self.flow.home.attach_text(status, name="login_status")
            print(f"\n完整登录流程结束，登录状态: {status}")

    # ---------------- teardown：恢复环境 ----------------
    def teardown(self) -> None:
        """恢复环境：无论执行成败均回到首页初始状态。"""
        with allure.step("恢复环境：回到首页"):
            try:
                self.driver.get(BilibiliHomePage.url)
                self.flow.home.wait_loaded(timeout=10)
            except Exception:
                pass


# ---------------- 用例入口（pytest 函数包装，teardown 由基类 run 保证必定执行） ----------------
@pytest.mark.ui
@pytest.mark.web
@allure.feature("哔哩哔哩")
@allure.story("登录场景")
@allure.title("打开哔哩哔哩首页进入登录页，按指定账号从 data 获取密码并输入")
def test_bilibili_login_scenario(driver):
    TestBilibiliLoginScenario(driver).run()


@pytest.mark.ui
@pytest.mark.web
@allure.feature("哔哩哔哩")
@allure.story("登录场景")
@allure.title("完整登录流程：业务流 login() 串联进入登录页、输入、提交与验证")
def test_bilibili_complete_login_flow(driver):
    TestBilibiliCompleteLoginFlow(driver).run()
