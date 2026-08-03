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
