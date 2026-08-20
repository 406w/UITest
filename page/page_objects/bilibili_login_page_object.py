"""哔哩哔哩登录页页面对象（PageObject 层）。

实现页面全部控件操作，暴露业务接口，链式调用。
"""
from __future__ import annotations

import allure

from page.page_elements import Page
from page.page_elements.bilibili_home_page import BilibiliHomePage
from page.page_elements.bilibili_login_page import BilibiliLoginPage
from page.page_objects import PageObject


class BilibiliLoginPageObject(PageObject):
    page = BilibiliLoginPage

    # ---------------- 页面操作 ----------------
    def open_login(self) -> "BilibiliLoginPageObject":
        return self.open()

    def wait_loaded(self, timeout: float = 20.0) -> "BilibiliLoginPageObject":
        self.operates.find(self.page, "login_btn", timeout=timeout)
        return self

    # ---------------- 输入与提交 ----------------
    def input_username(self, username: str) -> "BilibiliLoginPageObject":
        self.send_keys("username", username)
        return self

    def input_password(self, password: str) -> "BilibiliLoginPageObject":
        self.send_keys("password", password)
        return self

    def click_login(self, **kwargs) -> "BilibiliLoginPageObject":
        self.click("login_btn", **kwargs)
        return self

    def has_captcha(self, timeout: float = 3.0) -> bool:
        """登录提交后是否出现滑块验证码（geetest）。"""
        try:
            return self.find("captcha", timeout=timeout).is_displayed()
        except Exception:
            return False

    def login(self, username: str, password: str) -> "BilibiliLoginPageObject":
        """组合登录操作，链式调用。"""
        return (
            self.wait_loaded()
            .input_username(username)
            .input_password(password)
            .click_login()
        )

    # ---------------- 页面跳转 ----------------
    def go_home(self) -> "BilibiliHomePageObject":
        """按 PE 层 jump 跳转声明跳回首页。"""
        from page.page_objects.bilibili_home_page_object import BilibiliHomePageObject

        ways = Page.ways_to(BilibiliHomePage)
        login_ways = [w for w in ways if w[2] is self.page]
        if not login_ways:
            raise ValueError(
                f"PE 层未声明 {self.page.__name__} 能跳转到 {BilibiliHomePage.__name__} 的方式"
            )
        desc, cond, from_page, locator = login_ways[0]
        self.click(locator.name, expected="url")
        return BilibiliHomePageObject(self.driver, platform=self.platform)

    # ---------------- 报告辅助 ----------------
    def attach_screenshot(self, name: str = "bilibili_login") -> "BilibiliLoginPageObject":
        allure.attach(
            self.driver.get_screenshot_as_png(),
            name=name,
            attachment_type=allure.attachment_type.PNG,
        )
        return self

    def attach_text(self, text: str, name: str) -> "BilibiliLoginPageObject":
        allure.attach(text, name=name, attachment_type=allure.attachment_type.TEXT)
        return self
