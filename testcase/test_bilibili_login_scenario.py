"""测试用例层：哔哩哔哩登录场景。

场景：打开 Edge -> 进入哔哩哔哩首页 -> 进入登录页 -> 按指定账号从 data 获取密码并输入，
输入完成后即结束（不点击登录、不验证登录结果）。仅验证 web 端。
"""
# ---------------- 引入资源文件 ----------------
import allure
import pytest

from common.testcase.base_test_case import TestCaseBase
from data.database import DataBase
from page.page_elements.bilibili_home_page import BilibiliHomePage
from page.page_objects.bilibili_home_page_object import BilibiliHomePageObject

ACCOUNT_USERNAME = "NA"


class TestBilibiliLoginScenario(TestCaseBase):
    """哔哩哔哩登录场景用例。

    init -> 实例化操作对象
    setup -> 预置条件：取账号、打开首页、确认未登录
    test_step -> 测试步骤：进入登录页，输入账号密码
    teardown -> 恢复环境：回到首页
    """

    __test__ = False  # 非 pytest 测试类，由下方函数入口调用 run()

    # ---------------- init：初始化测试用例 ----------------
    def _init_objects(self) -> None:
        """引入资源文件并实例化操作对象。"""
        self.db = DataBase()
        self.home = BilibiliHomePageObject(self.driver, platform=self.platform)

    # ---------------- setup：预置条件 ----------------
    def setup(self) -> None:
        with allure.step("预置条件：从 data 获取指定账号的密码"):
            self.account = self.db.get_account(ACCOUNT_USERNAME, site_name="哔哩哔哩")
            assert self.account is not None, (
                f"data 中未找到账号 {ACCOUNT_USERNAME}，"
                f"现有账号: {[a['username'] for a in self.db.get_accounts('哔哩哔哩')]}"
            )
        with allure.step("预置条件：打开哔哩哔哩首页并确认未登录"):
            self.home.open_home().wait_loaded()
            if self.home.is_logged_in():
                pytest.skip("当前已登录，无法执行登录场景")

    # ---------------- test_step：测试步骤 ----------------
    def test_step(self) -> None:
        with allure.step("进入登录页"):
            login = self.home.go_to_login()
            login.wait_loaded()

        with allure.step(f"输入 data 中的账号 {self.account['username']} 与密码"):
            login.input_username(self.account["username"]).input_password(self.account["password"])
            login.attach_screenshot("login_filled")
            login.attach_text(
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
                self.home.wait_loaded(timeout=10)
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
