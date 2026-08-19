"""PageObject 层。

规则：
1. 关联 PageElement 层中单个页面的 Page 类
2. 实现该页面全部控件的全部操作
3. 暴露业务需要用到的接口
4. 链式调用
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from common.base_operates import BaseOperates

if TYPE_CHECKING:
    from page.page_elements import Page


class PageObject:
    """页面对象基类：绑定页面元素声明（Page）与基础操作（BaseOperates）。"""

    page: type["Page"]

    def __init__(self, driver, platform: str = "web", timeout: float = 10.0):
        self.driver = driver
        self.platform = platform
        self.operates = BaseOperates(driver, platform=platform, timeout=timeout)

    # ---------------- 基础能力 ----------------
    def open(self, url: str | None = None) -> "PageObject":
        package_name = getattr(self.page, "package_name", "")
        main_activity = getattr(self.page, "main_activity", "")
        if self.platform == "android" and package_name and main_activity:
            # 冷启动：先杀进程再拉起，强制回到主 Activity（消除 App 页面记忆，保证从首页开始）
            try:
                self.driver.terminate_app(package_name)
            except Exception:
                pass
            self.driver.activate_app(package_name)
            return self
        if self.platform in ("android", "ios") and package_name:
            self.driver.activate_app(package_name)
            return self
        self.driver.get(url or self.page.url)
        return self

    def find(self, name: str, **kwargs):
        return self.operates.find(self.page, name, **kwargs)

    def find_all(self, name: str, **kwargs):
        return self.operates.find_all(self.page, name, **kwargs)

    def send_keys(self, name: str, text: str, **kwargs):
        return self.operates.send_keys(self.page, name, text, **kwargs)

    def click(self, name: str, **kwargs):
        return self.operates.click(self.page, name, **kwargs)

    def swipe(self, name: str | None = None, **kwargs):
        return self.operates.swipe(self.page, name, **kwargs)

    def current_url(self) -> str:
        return self.driver.current_url

    def page_title(self) -> str:
        return self.driver.title

    def screenshot(self, path: str = "screenshot.png"):
        self.driver.save_screenshot(path)
        return self
