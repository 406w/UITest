from page.page_elements.login_page import LoginPage
from page.page_objects.home_po import BasePO
from page.page_objects.locator import jump


class LoginPO(BasePO):
    page_key = "login"
    elements = LoginPage

    def open(self):
        self.driver.get(self.context.config.base_url.rstrip("/") + "/#/dashboard")
        return self.wait_ready()

    def wait_ready(self):
        self.ops.find(lambda d: self.resolve(d, LoginPage.ready))
        return self

    def enter_username(self, value):
        self.element(LoginPage.username).fill(value)
        return self

    def enter_password(self, value):
        self.element(LoginPage.password).fill(value, sensitive=True)
        return self

    @jump(source="login", element_key="submit", target="home")
    def submit_success(self):
        self.element(LoginPage.submit).click()

    def submit_rejected(self):
        self.element(LoginPage.submit).click()
        self.ops.wait(lambda d: self.element(LoginPage.error).text(), "登录错误提示未出现")
        return self

    def error_text(self):
        return self.element(LoginPage.error).text()
