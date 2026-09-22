from selenium.webdriver.common.by import By

from common.base_operates import BaseOperates, ElementHandle
from common.elements import resolve_declared_element
from page.page_elements.home_page import HomePage
from page.page_objects.locator import jump


class BasePO:
    def __init__(self, context):
        self.context = context
        self.ops = BaseOperates(context)

    @property
    def driver(self):
        return self.context.driver

    def element(self, declaration):
        return ElementHandle(self.ops, declaration, lambda d: self.resolve(d, declaration))

    def resolve(self, driver, declaration):
        return resolve_declared_element(driver, declaration)


class HomePO(BasePO):
    page_key = "home"
    elements = HomePage

    def wait_ready(self):
        self.ops.find(lambda d: self.resolve(d, HomePage.ready))
        return self

    def resolve(self, driver, declaration):
        if declaration is HomePage.user_menu:
            return driver.find_element(By.CSS_SELECTOR, ".topbar .avatar + span")
        return super().resolve(driver, declaration)

    def current_user(self):
        return self.element(HomePage.user_menu).text().splitlines()[0]

    @jump(source="home", element_key="logout", target="login")
    def logout(self):
        self.element(HomePage.logout).click()

    @jump(source="home", element_key="sale", target="sale")
    def open_sale(self):
        self.element(HomePage.sale).click()

    @jump(source="home", element_key="purchase", target="purchase")
    def open_purchase(self):
        self.element(HomePage.purchase).click()
