"""测试用例层：哔哩哔哩页面自动化测试（类结构用例）。"""
# ---------------- 引入资源文件 ----------------
import allure
import pytest

from common.base_test_case import TestCaseBase
from page.page_objects.bilibili_home_page_object import BilibiliHomePageObject


class TestBilibiliHomepageLoginStatus(TestCaseBase):
    """检查哔哩哔哩首页登录状态。"""

    __test__ = False  # 非 pytest 测试类，由下方函数入口调用 run()

    # ---------------- init：初始化测试用例 ----------------
    def _init_objects(self) -> None:
        self.home = BilibiliHomePageObject(self.driver, platform=self.platform)

    # ---------------- setup：预置条件 ----------------
    def setup(self) -> None:
        with allure.step("预置条件：打开哔哩哔哩首页并等待加载完成"):
            self.home.open_home().wait_loaded()
            assert "哔哩哔哩" in self.home.page_title(), f"页面标题异常: {self.home.page_title()}"

    # ---------------- test_step：测试步骤 ----------------
    def test_step(self) -> None:
        with allure.step("检查登录状态"):
            logged_in = self.home.is_logged_in()

        with allure.step("记录登录状态与页面截图"):
            status = self.home.login_status()
            self.home.attach_screenshot().attach_text(status, name="login_status")
            assert isinstance(logged_in, bool)
            print(f"\n哔哩哔哩登录状态: {status}")

    # ---------------- teardown：恢复环境 ----------------
    def teardown(self) -> None:
        pass


class TestBilibiliHomepageToLoginPage(TestCaseBase):
    """从首页按 PageRedirect 跳转关系进入登录页。"""

    __test__ = False  # 非 pytest 测试类，由下方函数入口调用 run()

    # ---------------- init：初始化测试用例 ----------------
    def _init_objects(self) -> None:
        self.home = BilibiliHomePageObject(self.driver, platform=self.platform)

    # ---------------- setup：预置条件 ----------------
    def setup(self) -> None:
        with allure.step("预置条件：打开首页并确认未登录"):
            self.home.open_home().wait_loaded()
            if self.home.is_logged_in():
                pytest.skip("当前已登录，首页无登录入口可跳转")

    # ---------------- test_step：测试步骤 ----------------
    def test_step(self) -> None:
        with allure.step("按跳转关系点击登录入口进入登录页"):
            login = self.home.go_to_login()
            login.wait_loaded()

        with allure.step("校验已进入登录页"):
            assert login.find("username", timeout=5, wait_visible=True).is_displayed(), (
                f"未进入登录页: {login.current_url()}"
            )
            login.attach_screenshot("login_page")

        with allure.step("在登录页输入账号密码"):
            login.input_username("test_user").input_password("test_pass")
            login.attach_screenshot("login_page_filled")

    # ---------------- teardown：恢复环境 ----------------
    def teardown(self) -> None:
        pass


# ---------------- 用例入口（pytest 函数包装，teardown 由基类 run 保证必定执行） ----------------
@pytest.mark.ui
@pytest.mark.web
@allure.feature("哔哩哔哩")
@allure.story("登录状态检查")
@allure.title("在 Edge 浏览器打开哔哩哔哩首页并检查登录状态")
def test_bilibili_homepage_login_status(driver):
    TestBilibiliHomepageLoginStatus(driver).run()


@pytest.mark.ui
@pytest.mark.web
@allure.feature("哔哩哔哩")
@allure.story("页面跳转")
@allure.title("从首页按 PageRedirect 跳转关系进入登录页")
def test_bilibili_homepage_to_login_page(driver):
    TestBilibiliHomepageToLoginPage(driver).run()
