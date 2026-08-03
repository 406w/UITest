"""BaseOperates 层：基础操作。

find 方法重构
1. 声明不同函数对定位器不同属性的控件进行查找（find / find_all / find_by_text ...）
2. 自动获取类中对应的属性（页面类中的 Locator / Relation）
3. 软等待
4. 第二线程并行滚动，辅助查找

click 方法重构
1. 获取当前页面快照，对比操作后的实际结果
2. 允许传入处理指定弹窗的处理函数
3. 截获可能出现的弹窗，如果弹窗不是目标弹窗，给出实际报错原因

swipe 方法重构
1. 按照实际的手势操作进行
2. 处理控件只出现一部分的情况
3. 处理反弹问题
"""
from __future__ import annotations

import threading
import time
from typing import Callable

from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from page.page_elements import ElementResolver, Page

POPUP_SELECTORS = (
    "div.layui-layer",
    "div[class*='dialog']",
    "div[class*='modal']",
    "div[class*='popup']",
    "div[class*='toast']",
    "div[class*='toast-container']",
    "div[class*='message']",
    "div[class*='alert']",
)


class PopupError(AssertionError):
    """截获到非目标弹窗。"""


class ElementNotFoundError(AssertionError):
    """元素查找失败。"""


class ClickResult:
    """click 操作后的结果：快照对比 + 弹窗处理记录。"""

    def __init__(self):
        self.url_changed = False
        self.title_changed = False
        self.popup_handled: bool | None = None
        self.popup_text: str | None = None
        self.success = True

    def __repr__(self) -> str:
        return (
            f"<ClickResult url_changed={self.url_changed} "
            f"title_changed={self.title_changed} popup_handled={self.popup_handled}>"
        )


class BaseOperates:
    def __init__(self, driver, platform: str = "web", timeout: float = 10.0):
        self.driver = driver
        self.platform = platform
        self.timeout = timeout
        self._resolver = ElementResolver(platform, timeout)

    # ---------------------------------------------------------------
    # find 方法重构
    # ---------------------------------------------------------------
    def _element_for(self, page: type[Page], name: str) -> type:
        element_cls = page.get_element(name)
        if element_cls is None:
            raise ValueError(f"页面 {page.__name__} 中未声明控件: {name}")
        return element_cls

    def find(
        self,
        page: type[Page],
        name: str,
        timeout: float | None = None,
        wait_visible: bool = True,
        scroll: bool = False,
    ) -> WebElement:
        """软等待查找单个元素。scroll=True 时启用第二线程并行滚动辅助查找。"""
        element_cls = self._element_for(page, name)
        timeout = timeout if timeout is not None else self.timeout
        deadline = time.monotonic() + timeout

        # 关系定位控件：自动解析"关系"，转换为实际定位器（软等待重试）
        platform_cls = getattr(element_cls, self.platform, None)
        if isinstance(platform_cls, type) and getattr(platform_cls, "relation", None):
            last_error: Exception | None = None
            while time.monotonic() < deadline:
                try:
                    return self._resolver.resolve(self.driver, element_cls)
                except Exception as exc:
                    last_error = exc
                    time.sleep(0.5)
            raise ElementNotFoundError(
                f"查找失败(关系定位): {page.__name__}.{name} "
                f"({element_cls.element_name}) 等待 {timeout}s 未找到: {last_error}"
            ) from None

        by, value = self._resolver.locate_by(element_cls)

        if not scroll:
            condition = EC.visibility_of_element_located if wait_visible else EC.presence_of_element_located
            try:
                return WebDriverWait(self.driver, timeout).until(condition((by, value)))
            except TimeoutException:
                raise ElementNotFoundError(
                    f"查找失败: {page.__name__}.{name} ({element_cls.element_name}) "
                    f"等待 {timeout}s 未找到"
                ) from None

        result: list[WebElement] = []
        stop = threading.Event()

        def scroll_searcher():
            while time.monotonic() < deadline and not stop.is_set():
                try:
                    el = self.driver.find_element(by, value)
                    if not wait_visible or el.is_displayed():
                        result.append(el)
                        stop.set()
                        return
                except NoSuchElementException:
                    pass
                self.swipe(page, name, direction="down", duration=300)
            stop.set()

        thread = threading.Thread(target=scroll_searcher, daemon=True)
        thread.start()
        thread.join(timeout=timeout + 1)
        if result:
            return result[0]
        raise ElementNotFoundError(
            f"查找失败(并行滚动后): {page.__name__}.{name} "
            f"({element_cls.element_name}) 等待 {timeout}s 未找到"
        )

    def find_all(
        self,
        page: type[Page],
        name: str,
        timeout: float | None = None,
    ) -> list[WebElement]:
        element_cls = self._element_for(page, name)
        by, value = self._resolver.locate_by(element_cls)
        timeout = timeout if timeout is not None else self.timeout
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            elements = self.driver.find_elements(by, value)
            if elements:
                return elements
            time.sleep(0.5)
        return []

    def find_by_text(
        self,
        text: str,
        tag: str = "*",
        timeout: float | None = None,
    ) -> WebElement:
        """按文本查找（适用于无特征属性的控件）。"""
        timeout = timeout if timeout is not None else self.timeout
        condition = EC.presence_of_element_located((By.XPATH, f"//{tag}[contains(text(), '{text}')]"))
        try:
            return WebDriverWait(self.driver, timeout).until(condition)
        except TimeoutException:
            raise ElementNotFoundError(f"按文本查找失败: '{text}'") from None

    def send_keys(
        self,
        page: type[Page],
        name: str,
        text: str,
        clear: bool = True,
        timeout: float | None = None,
        scroll: bool = False,
    ) -> WebElement:
        """向控件输入文本（默认先清空）。"""
        element = self.find(page, name, timeout=timeout, scroll=scroll)
        if clear:
            element.clear()
        element.send_keys(text)
        return element

    # ---------------------------------------------------------------
    # click 方法重构
    # ---------------------------------------------------------------
    def _snapshot(self) -> dict:
        try:
            url = self.driver.current_url
        except Exception:
            url = ""
        try:
            title = self.driver.title
        except Exception:
            title = ""
        return {"url": url, "title": title}

    def _looks_like_popup(self, el) -> bool:
        """web 平台弹窗校验：覆盖面积 >= 视口 10% 且中心在视口内（排除底部小提示条）。"""
        try:
            return bool(
                self.driver.execute_script(
                    "const el = arguments[0];"
                    "const r = el.getBoundingClientRect();"
                    "const vw = window.innerWidth, vh = window.innerHeight;"
                    "const cx = r.left + r.width / 2, cy = r.top + r.height / 2;"
                    "return r.width * r.height >= vw * vh * 0.1"
                    "  && cx >= 0 && cx <= vw && cy >= 0 && cy <= vh;",
                    el,
                )
            )
        except Exception:
            return False

    def _detect_popup(self) -> WebElement | None:
        for selector in POPUP_SELECTORS:
            try:
                elements = self.driver.find_elements("css selector", selector)
                for el in elements:
                    if el.is_displayed():
                        if self.platform == "web" and not self._looks_like_popup(el):
                            continue
                        return el
            except Exception:
                continue
        return None

    def click(
        self,
        page: type[Page],
        name: str,
        popup_handler: Callable[[WebElement, str], bool] | None = None,
        expected: str | None = None,
        timeout: float | None = None,
        scroll: bool = False,
    ) -> ClickResult:
        """点击重构：快照对比 + 弹窗截获。

        popup_handler: 传入处理指定弹窗的函数，签名 (popup_element, popup_text) -> bool
            返回 True 表示弹窗已按预期处理。
        expected: 点击后预期结果，可选 "url" / "title" / None(不校验)
        """
        before = self._snapshot()
        element = self.find(page, name, timeout=timeout, scroll=scroll)
        try:
            element.click()
        except Exception as exc:
            # 元素被遮挡等场景：真实手势点击
            try:
                ActionChains(self.driver).move_to_element(element).click().perform()
            except Exception:
                raise exc

        result = ClickResult()
        time.sleep(0.5)

        # 截获可能出现的弹窗
        popup = self._detect_popup()
        if popup is not None:
            try:
                result.popup_text = popup.text.strip()[:200]
            except Exception:
                result.popup_text = ""
            if popup_handler is not None:
                handled = popup_handler(popup, result.popup_text)
                result.popup_handled = bool(handled)
                if not handled:
                    raise PopupError(
                        f"点击 {page.__name__}.{name} 后出现弹窗，目标弹窗处理函数返回 False: {result.popup_text}"
                    )
            else:
                raise PopupError(
                    f"点击 {page.__name__}.{name} 后截获到未预期的弹窗: {result.popup_text}。"
                    f"如为目标弹窗，请传入 popup_handler 处理；否则为实际页面异常。"
                )

        # 快照对比
        after = self._snapshot()
        result.url_changed = before["url"] != after["url"]
        result.title_changed = before["title"] != after["title"]
        if expected == "url" and not result.url_changed:
            result.success = False
            raise AssertionError(
                f"点击 {page.__name__}.{name} 后 URL 未发生变化，页面跳转失败"
            )
        if expected == "title" and not result.title_changed:
            result.success = False
            raise AssertionError(
                f"点击 {page.__name__}.{name} 后页面标题未发生变化"
            )
        return result

    # ---------------------------------------------------------------
    # swipe 方法重构
    # ---------------------------------------------------------------
    def swipe(
        self,
        page: type[Page] | None = None,
        name: str | None = None,
        direction: str = "up",
        distance: int | None = None,
        duration: int = 500,
        times: int = 1,
    ) -> None:
        """按照实际手势操作进行滑动。

        - 处理控件只出现一部分的情况：滑动距离自动适配视口
        - 处理反弹问题：检测到达边界后做反向补偿
        """
        size = self.driver.get_window_size()
        vw, vh = size["width"], size["height"]
        distance = distance or int(vh * 0.7)

        if self.platform == "web":
            return self._swipe_web(direction, distance, duration, times)
        return self._swipe_appium(direction, distance, duration, times)

    def _swipe_web(self, direction: str, distance: int, duration: int, times: int):
        js = {
            "up": f"window.scrollBy(0, {distance});",
            "down": f"window.scrollBy(0, -{distance});",
            "left": f"window.scrollBy({distance}, 0);",
            "right": f"window.scrollBy(-{distance}, 0);",
        }[direction]
        for _ in range(times):
            before = self.driver.execute_script("return window.scrollY")
            self.driver.execute_script(js)
            time.sleep(duration / 1000)
            after = self.driver.execute_script("return window.scrollY")
            if abs(after - before) < 1:
                # 到达边界，反弹补偿：向反方向回滚一点
                bounce = {"up": "window.scrollBy(0, -40);", "down": "window.scrollBy(0, 40);"}.get(direction)
                if bounce:
                    self.driver.execute_script(bounce)
                break

    def _swipe_appium(self, direction: str, distance: int, duration: int, times: int):
        size = self.driver.get_window_size()
        w, h = size["width"], size["height"]
        if direction == "up":
            start, end = (w / 2, h * 0.8), (w / 2, h * 0.2)
        elif direction == "down":
            start, end = (w / 2, h * 0.2), (w / 2, h * 0.8)
        elif direction == "left":
            start, end = (w * 0.8, h / 2), (w * 0.2, h / 2)
        else:
            start, end = (w * 0.2, h / 2), (w * 0.8, h / 2)
        try:
            self.driver.swipe(*start, *end, duration)
        except Exception:
            from selenium.webdriver.common.touch_actions import TouchActions

            TouchActions(self.driver).flick(*start, *end).perform()
