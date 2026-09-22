from selenium.webdriver.common.by import By

from common.base_operates import log
from common.config import Context
from common.report import default_title
from data.database import Account
from page.page_objects.home_po import HomePO
from page.page_objects.login_po import LoginPO


class AW:
    def __init__(self, context: Context) -> None:
        self.context = context

    def open_webpage(self) -> LoginPO:
        default_title("step", "打开 ERP 网页")
        return LoginPO(self.context).open()

    def login_as(self, account: Account) -> HomePO:
        default_title("step", "使用测试账号登录")
        return (self.open_webpage().enter_username(account.username)
                .enter_password(account.password).submit_success())

    def logout(self) -> LoginPO:
        default_title("step", "退出登录")
        return HomePO(self.context).logout()

    def logout_if_logged_in(self):
        driver = self.context.driver
        if driver and driver.find_elements(By.CSS_SELECTOR, '[data-action="logout"]'):
            modal = driver.find_elements(By.CSS_SELECTOR, '#modal[open] [aria-label="关闭弹窗"]')
            if modal:
                modal[0].click()
            self.logout()

    def open_orders(self, order_type):
        home = HomePO(self.context)
        if order_type == "sale":
            return home.open_sale()
        if order_type == "purchase":
            return home.open_purchase()
        raise ValueError("订单类型必须为 sale/purchase")

    def refresh(self):
        self.context.driver.refresh()
        log.info("刷新页面")

    def get_cookie(self, cookie_name):
        return self.context.driver.get_cookie(cookie_name)
