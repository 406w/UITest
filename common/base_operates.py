import logging
import time

from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException, TimeoutException
from selenium.webdriver import ActionChains
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from common.elements import description
from common.report import screenshot

log = logging.getLogger(__name__)


class BaseOperates:
    def __init__(self, context):
        self.context = context

    def find(self, resolver, condition="visible", required=True, scroll_container=None, label="元素"):
        if condition not in {"present", "visible", "clickable", "editable"}:
            raise ValueError(f"未知等待条件：{condition}")
        deadline = time.monotonic() + self.context.config.timeout
        while True:
            try:
                element = resolver(self.context.driver)
                ready = condition == "present" or element.is_displayed()
                if condition in {"clickable", "editable"}:
                    ready = ready and element.is_enabled()
                if condition == "editable":
                    ready = ready and element.get_dom_attribute("readonly") is None
                if ready:
                    return element
            except (NoSuchElementException, StaleElementReferenceException):
                pass
            if time.monotonic() >= deadline:
                if required:
                    raise TimeoutException(f"等待 {label} 达到 {condition} 超时（{self.context.config.timeout}s）")
                return None
            if scroll_container:
                container = scroll_container(self.context.driver)
                self.context.driver.execute_script("arguments[0].scrollTop += 150", container)
            time.sleep(self.context.config.poll_interval)

    def wait(self, predicate, message):
        return WebDriverWait(self.context.driver, self.context.config.timeout,
                             poll_frequency=self.context.config.poll_interval,
                             ignored_exceptions=(NoSuchElementException, StaleElementReferenceException)).until(
                                 predicate, message)

    def click(self, resolver, label, alert_policy="fail"):
        if alert_policy not in {"fail", "accept", "dismiss"}:
            raise ValueError("alert_policy 必须为 fail/accept/dismiss")
        element = self.find(resolver, "clickable", label=label)
        if self.context.config.click_snapshots:
            screenshot(self.context, "点击前：" + label)
        element.click()  # 不重放已经发出的点击/提交。
        if alert_policy != "fail":
            alert = self.wait(EC.alert_is_present(), "等待预期弹窗超时")
            getattr(alert, alert_policy)()
        if self.context.config.click_snapshots:
            screenshot(self.context, "点击后：" + label)

    def swipe(self, resolver, direction="down", distance=300):
        if direction not in {"up", "down", "left", "right"} or distance <= 0:
            raise ValueError("无效的手势方向或距离")
        element = self.find(resolver)
        dx = distance * ({"left": -1, "right": 1}.get(direction, 0))
        dy = distance * ({"up": -1, "down": 1}.get(direction, 0))
        from selenium.webdriver.common.actions.wheel_input import ScrollOrigin
        ActionChains(self.context.driver).scroll_from_origin(ScrollOrigin.from_element(element), dx, dy).perform()


class ElementHandle:
    def __init__(self, ops, declaration, resolver):
        self.ops, self.declaration, self.resolver = ops, declaration, resolver
        self.description = description(declaration)

    def fill(self, value, sensitive=False):
        if sensitive:
            self.ops.context.secrets.add(str(value))
        element = self.ops.find(self.resolver, "editable", label=self.description)
        if sensitive:
            self.ops.context.driver.execute_script("arguments[0].setAttribute('data-ui-sensitive', '')", element)
        element.clear()
        element.send_keys(str(value))
        log.info("输入 %s：%s", self.description, "***" if sensitive else self.ops.context.redact(value))
        return self

    def click(self, alert_policy="fail"):
        self.ops.click(self.resolver, self.description, alert_policy)
        return self

    def select(self, *, text=None, value=None):
        if (text is None) == (value is None):
            raise ValueError("必须且只能提供 text 或 value")
        control = Select(self.ops.find(self.resolver, "editable", label=self.description))
        if text is not None:
            control.select_by_visible_text(text)
        else:
            control.select_by_value(str(value))
        return self

    def text(self):
        return self.ops.find(self.resolver, label=self.description).text.strip()

    def attribute(self, name):
        return self.ops.find(self.resolver, label=self.description).get_attribute(name)

