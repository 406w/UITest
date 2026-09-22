import allure

from common.action_write import AW
from common.base_checks import BaseChecks
from common.config import Context
from common.report import run_phase
from data.database import Database


class TestCase:
    """用例的公共属性在此显式定义，子类可直接补全和跳转。"""

    __test__ = False
    context: Context
    database: Database
    aw: AW
    checks: BaseChecks
    title: str

    def bind_resources(self, context: Context, database: Database) -> None:
        """框架在 init 前调用；资源定义和业务对象创建均归属用例基类。"""
        self.context = context
        self.database = database
        self.aw = AW(context)
        self.checks = BaseChecks(context)
        self.title = type(self).__name__

    def init(self) -> None:
        pass

    def setup(self) -> None:
        pass

    def process(self) -> None:
        raise NotImplementedError("用例必须实现 process(self)")

    def teardown(self) -> None:
        pass

    def test_process(self):
        # Allure 在 pytest setup 结束后才设置默认名称，必须在 call 阶段覆盖。
        allure.dynamic.title(getattr(self, "title", type(self).__name__))
        run_phase("process：测试步骤", self.process, self.context)
