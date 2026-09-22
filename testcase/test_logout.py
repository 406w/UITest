import allure
import pytest

from common.report import checkpoint, step
from common.test_case import TestCase


@pytest.mark.ui
@pytest.mark.smoke
@allure.feature("退出登录")
class TestLogout(TestCase):
    __test__ = True

    def init(self):
        self.title = "退出登录后刷新不能恢复会话"
        self.account = self.database.account("admin")

    def setup(self):
        step("预置步骤：登录 ERP")
        self.aw.login_as(self.account)

    def process(self):
        step("步骤1：点击退出登录")
        login = self.aw.logout()

        checkpoint("检查点1：会话 cookie 已清除")
        self.checks.equal(self.context.driver.get_cookie("erp_session"), None, "会话 cookie")

        step("步骤2：刷新页面")
        self.context.driver.refresh()
        login.wait_ready()

        checkpoint("检查点2：仍显示登录页")
        from page.page_elements.login_page import LoginPage
        self.checks.equal(login.element(LoginPage.submit).text(), "登录工作台 →", "登录按钮")

    def teardown(self):
        self.aw.logout_if_logged_in()
