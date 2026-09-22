"""标题式 Allure 步骤。业务脚本不需要 with。"""
import logging
import sys
from contextvars import ContextVar
from urllib.parse import urlsplit, urlunsplit

import allure

log = logging.getLogger(__name__)
_active = ContextVar("erp_ui_report", default=None)


class ReportUsageError(RuntimeError):
    pass


class StepReporter:
    def __init__(self, context=None):
        self.context = context
        self.current = None
        self.kind = None

    def has_title(self):
        return self.current is not None

    def begin(self, kind, title):
        if not isinstance(title, str) or not title.strip():
            raise ValueError("步骤标题不能为空")
        self.finish()
        scope = allure.step(title)
        scope.__enter__()
        self.current, self.kind = scope, kind
        # 先进入 Allure 步骤再附加截图，使图片归属当前标题，而非上一条步骤。
        screenshot(self.context, f"步骤开始：{title}")

    def finish(self, exc_info=(None, None, None)):
        scope, self.current = self.current, None
        self.kind = None
        if scope is not None:
            scope.__exit__(*exc_info)


def current_report():
    reporter = _active.get()
    if reporter is None:
        raise ReportUsageError("step/checkpoint 必须在用例生命周期内调用")
    return reporter


def step(title):
    current_report().begin("step", title)


def checkpoint(title):
    current_report().begin("checkpoint", title)


def default_title(kind, title):
    if not current_report().has_title():
        current_report().begin(kind, title)


def attach_text(title, text, context=None):
    try:
        value = context.redact(text) if context else str(text)
        allure.attach(value, name=title, attachment_type=allure.attachment_type.TEXT)
    except Exception:
        log.exception("报告文本附件失败")


def screenshot(context, title):
    if context is None or not context.config.screenshots or context.driver is None:
        return False
    driver = context.driver
    token = None
    try:
        # 仅暂时隐藏敏感输入及示例页面密码提示，finally 恢复原样式。
        token = driver.execute_script("""
            const nodes = [...document.querySelectorAll(
              'input[type="password"], [data-ui-sensitive], .demo-accounts')];
            const state = nodes.map(el => [el, el.style.visibility]);
            nodes.forEach(el => el.style.visibility = 'hidden');
            return state;
        """)
        allure.attach(driver.get_screenshot_as_png(), name=title,
                      attachment_type=allure.attachment_type.PNG)
        return True
    except Exception:
        log.warning("截图失败（保留原测试结果）", exc_info=True)
        return False
    finally:
        if token is not None:
            try:
                driver.execute_script("arguments[0].forEach(([el,v]) => el.style.visibility=v)", token)
            except Exception:
                log.debug("截图样式恢复失败，页面可能已跳转", exc_info=True)


def capture_failure_safely(context, phase=None):
    if context is None or context.phase in context.evidence_phases:
        return
    title = phase or context.phase
    try:
        captured = screenshot(context, f"失败截图：{title}")
        if context.driver is not None:
            parts = urlsplit(context.driver.current_url)
            # 不保存 query/fragment，避免 URL 中包含凭据。
            attach_text("失败页面", urlunsplit((parts.scheme, parts.netloc, parts.path, "", "")), context)
        if captured:
            context.evidence_phases.add(context.phase)
    except Exception:
        log.warning("失败证据采集异常", exc_info=True)


def _close_preserving(scope, exc_info):
    try:
        scope.__exit__(*exc_info)
    except BaseException:
        log.exception("关闭报告容器失败，保留原异常")


def run_phase(title, action, context=None):
    reporter = StepReporter(context)
    token = _active.set(reporter)
    scope = allure.step(title)
    try:
        scope.__enter__()
        try:
            result = action()
            reporter.finish()
        except BaseException:
            error = sys.exc_info()
            capture_failure_safely(context, title)
            try:
                reporter.finish(error)
            except BaseException:
                log.exception("关闭标题步骤失败，保留原异常")
            _close_preserving(scope, error)
            raise
        else:
            scope.__exit__(None, None, None)
            return result
    finally:
        _active.reset(token)
