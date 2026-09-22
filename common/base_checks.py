import time

from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException

from common.report import attach_text, default_title
from common.config import Context


class BaseChecks:
    def __init__(self, context: Context | None = None) -> None:
        self.context = context

    def equal(self, actual, expected, description):
        default_title("checkpoint", description)
        detail = f"{description}\n预期：{expected!r}\n实际：{actual!r}"
        if self.context:
            detail = self.context.redact(detail)
        attach_text("校验结果", detail)
        assert actual == expected, detail

    def eventually(self, read_actual, expected, description, timeout=None):
        default_title("checkpoint", description)
        timeout = timeout if timeout is not None else self.context.config.timeout
        deadline = time.monotonic() + timeout
        actual = "尚未读取"
        while True:
            try:
                actual = read_actual()
                if actual == expected:
                    break
            except (NoSuchElementException, StaleElementReferenceException):
                actual = "元素尚未就绪"
            if time.monotonic() >= deadline:
                break
            time.sleep(0.1)
        self.equal(actual, expected, description)
