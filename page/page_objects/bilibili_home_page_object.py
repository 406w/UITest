"""哔哩哔哩首页页面对象（PageObject 层）。

实现页面全部控件操作，暴露业务接口，链式调用。
"""
from __future__ import annotations

import time

import allure

from page.page_elements import Page
from page.page_elements.bilibili_home_page import BilibiliHomePage
from page.page_elements.bilibili_login_page import BilibiliLoginPage
from page.page_objects import PageObject

LOGIN_COOKIES = ("SESSDATA", "DedeUserID")


class BilibiliHomePageObject(PageObject):
    page = BilibiliHomePage

    # ---------------- 页面操作 ----------------
    def open_home(self) -> "BilibiliHomePageObject":
        return self.open()

    def wait_loaded(self, timeout: float = 20.0) -> "BilibiliHomePageObject":
        self.operates.find(self.page, "home_header", timeout=timeout)
        return self

    # ---------------- 页面跳转 ----------------
    def go_to_login(self) -> "BilibiliLoginPageObject":
        """按 PE 层 jump 跳转声明跳转到登录页（仅未登录态存在登录入口）。"""
        from page.page_objects.bilibili_login_page_object import BilibiliLoginPageObject

        if self.is_logged_in():
            raise ValueError("当前已登录，首页无登录入口，无法跳转登录页")

        ways = [w for w in Page.ways_to(BilibiliLoginPage) if w[2] is self.page]
        if not ways:
            raise ValueError(
                f"PE 层未声明 {self.page.__name__} 能跳转到 {BilibiliLoginPage.__name__} 的方式"
            )
        for desc, cond, from_page, locator in ways:
            try:
                element = self.find(locator.name, timeout=2)
                if element.is_displayed():
                    self.click(locator.name)
                    return BilibiliLoginPageObject(self.driver, platform=self.platform)
            except Exception:
                continue
        raise ValueError(
            f"首页 {', '.join(w[2].name for w in ways)} 均不可点击，无法跳转登录页"
        )

    # ---------------- 业务接口 ----------------
    def is_logged_in(self) -> bool:
        """检查当前是否登录：登录/未登录入口 DOM 信号优先，cookie 兜底。"""
        for _ in range(20):
            for entry in ("login_entry", "go_login_btn"):
                try:
                    if self.find(entry, timeout=1, wait_visible=True).is_displayed():
                        return False
                except Exception:
                    pass
            try:
                if self.find("avatar", timeout=1, wait_visible=True).is_displayed():
                    return True
            except Exception:
                pass
            time.sleep(0.5)
        cookie_names = {c["name"] for c in self.driver.get_cookies()}
        return bool(set(LOGIN_COOKIES) & cookie_names)

    def login_status(self) -> str:
        return "已登录" if self.is_logged_in() else "未登录"

    # ---------------- “我的”功能入口（对应文本用例点击“我的”） ----------------
    def click_my(self) -> "BilibiliHomePageObject":
        """点击底部/入口的“我的”（PE 层 account 控件，多端适配）。"""
        self.click("account")
        return self

    def click_avatar(self) -> "BilibiliHomePageObject":
        """点击头像（登录后进入个人中心/触发昵称展示）。"""
        self.click("avatar")
        return self

    def get_nickname(self) -> str:
        """读取用户昵称文本，返回去空白后的字符串。"""
        return self.find("nickname", timeout=10, wait_visible=True).text.strip()

    def attach_screenshot(self, name: str = "bilibili_homepage") -> "BilibiliHomePageObject":
        allure.attach(
            self.driver.get_screenshot_as_png(),
            name=name,
            attachment_type=allure.attachment_type.PNG,
        )
        return self

    def attach_text(self, text: str, name: str) -> "BilibiliHomePageObject":
        allure.attach(text, name=name, attachment_type=allure.attachment_type.TEXT)
        return self
