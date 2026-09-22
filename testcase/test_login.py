import allure
import pytest

from common.report import checkpoint, step
from common.test_case import TestCase


@pytest.mark.ui
@pytest.mark.smoke
@allure.feature("登录")
class TestLogin(TestCase):
    __test__ = True

    def init(self):
        self.title = "有效账号登录 ERP"
        # 公共属性的定义及创建见 TestCase.bind_resources。
        self.account = self.database.account("admin")


    def setup(self):
        pass

    def process(self):
        step("步骤1：打开网页")
        login = self.aw.open_webpage()

        step("步骤2：输入账号密码并登录")
        home = (login.enter_username(self.account.username)
                .enter_password(self.account.password).submit_success())

        checkpoint("检查点1：首页展示当前登录用户")
        self.checks.equal(home.current_user(), self.account.expected_display_name, "当前用户")

        step("步骤3：刷新页面")
        self.aw.refresh()
        home.wait_ready()

        checkpoint("检查点2：刷新后登录会话仍有效")
        self.checks.equal(home.current_user(), self.account.expected_display_name, "刷新后的用户")

    def teardown(self):
        step("恢复步骤：退出当前测试会话")
        self.aw.logout_if_logged_in()


@pytest.mark.ui
@allure.feature("登录")
class TestInvalidPassword(TestCase):
    __test__ = True

    def init(self):
        self.title = "错误密码不能登录"
        # 公共属性的定义及创建见 TestCase.bind_resources。
        self.account = self.database.account("admin")

    def setup(self):
        pass

    def process(self):
        step("步骤1：打开登录页")
        login = self.aw.open_webpage()

        step("步骤2：使用错误密码登录")
        login.enter_username(self.account.username).enter_password("invalid-ui-password").submit_rejected()

        checkpoint("检查点1：展示登录失败提示")
        self.checks.equal(login.error_text(), "用户名或密码错误", "错误提示")

        checkpoint("检查点2：未创建登录会话")
        self.checks.equal(self.aw.get_cookie("erp_session"), None, "会话 cookie")

    def teardown(self):
        self.aw.logout_if_logged_in()
