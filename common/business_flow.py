"""业务流程层：串联各 PO 层的操作，形成可复用的业务场景。

规则：
1. 根据实际的测试操作，串联各种 PO 层的操作，比如：
   "登录"流程 = 打开首页 + 进入登录页 + 输入账号密码 + 提交 + 验证登录成功
2. 业务流类继承 BusinessFlow，在 _init_objects 中实例化涉及的 PO 对象与数据源
3. 流程方法内部以 allure.step 组织步骤，用例只调用业务流方法，不直接接触 PO 链式细节
4. 同时提供完整流程与分步方法，便于用例复用其中的部分步骤
"""
from __future__ import annotations

import time

import allure
import pytest

from data.database import DataBase
from page.page_objects.bilibili_home_page_object import BilibiliHomePageObject
from page.page_objects.bilibili_login_page_object import BilibiliLoginPageObject


class BusinessFlow:
    """业务流程基类：持有 driver，并实例化该流程涉及的 PO 对象与数据源。"""

    def __init__(self, driver, platform: str = "web"):
        self.driver = driver
        self.platform = platform
        self._init_objects()

    def _init_objects(self) -> None:
        """实例化涉及的 PO 对象与数据源，子类覆盖。"""


class BilibiliLoginFlow(BusinessFlow):
    """哔哩哔哩登录业务流：串联首页 / 登录页 PO 与 data 数据源。"""

    def _init_objects(self) -> None:
        self.home = BilibiliHomePageObject(self.driver, platform=self.platform)
        self.login = BilibiliLoginPageObject(self.driver, platform=self.platform)
        self.db = DataBase()

    # ---------------- 数据 ----------------
    def get_account(self, username: str, site_name: str = "哔哩哔哩") -> dict:
        """从 data 获取指定账号的密码，未找到时给出明确的失败原因。"""
        with allure.step(f"从 data 获取账号 {username} 的密码"):
            account = self.db.get_account(username, site_name=site_name)
            assert account is not None, (
                f"data 中未找到账号 {username}，"
                f"现有账号: {[a['username'] for a in self.db.get_accounts(site_name)]}"
            )
            return account

    # ---------------- 分步流程 ----------------
    def open_home(self) -> "BilibiliLoginFlow":
        """打开哔哩哔哩首页并等待加载完成。"""
        with allure.step("打开哔哩哔哩首页并等待加载完成"):
            self.home.open_home().wait_loaded()
        return self

    def ensure_not_logged_in(self) -> "BilibiliLoginFlow":
        """预置条件：确认当前未登录，已登录则跳过登录流程。"""
        with allure.step("确认当前未登录"):
            if self.home.is_logged_in():
                pytest.skip("当前已登录，无法执行登录流程")
        return self

    def go_to_login_page(self) -> "BilibiliLoginFlow":
        """从首页按跳转关系进入登录页。"""
        with allure.step("从首页进入登录页"):
            self.login = self.home.go_to_login()
            self.login.wait_loaded()
        return self

    def fill_login_form(self, username: str, password: str) -> "BilibiliLoginFlow":
        """在登录页输入账号密码（不提交）。"""
        with allure.step(f"输入账号 {username} 与密码"):
            self.login.input_username(username).input_password(password)
            self.login.attach_screenshot("login_filled")
        return self

    def submit_login(self, verify: bool = True) -> "BilibiliLoginFlow":
        """点击登录按钮提交；verify=True 时校验回到首页已登录态。"""
        with allure.step("点击登录按钮提交"):
            self.login.click_login()
            time.sleep(1)
        if verify:
            with allure.step("验证登录成功"):
                assert self.home.is_logged_in(), (
                    "点击登录后未处于已登录状态，可能遇到验证码或账号密码错误"
                )
                self.home.attach_screenshot("login_success")
        return self

    # ---------------- 完整流程 ----------------
    def login(self, username: str, password: str, verify: bool = True) -> "BilibiliLoginFlow":
        """完整登录流程：打开首页 -> 确认未登录 -> 进入登录页 -> 输入 -> 提交 -> 验证。"""
        return (
            self.open_home()
            .ensure_not_logged_in()
            .go_to_login_page()
            .fill_login_form(username, password)
            .submit_login(verify=verify)
        )
