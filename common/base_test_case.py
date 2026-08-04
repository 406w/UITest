"""用例层基类：测试用例脚本框架。

用例类标准结构：
- __init__(driver): init，初始化测试用例，引入资源文件，实例化操作对象
- setup():        预置条件
- test_step():    测试步骤（子类必须实现）
- teardown():     恢复环境（无论执行成功与否都会执行）

执行入口 run()：setup -> test_step，teardown 在 finally 中必定执行。
"""
from __future__ import annotations


class TestCaseBase:
    __test__ = False  # 标记非 pytest 测试类，由函数包装调用 run()

    def __init__(self, driver, platform: str = "web"):
        """init：初始化测试用例。driver 由 conftest fixture 注入。"""
        self.driver = driver
        self.platform = platform
        self._init_objects()

    def _init_objects(self) -> None:
        """初始化测试用例：引入资源文件（data/PO 等）并实例化操作对象，子类覆盖。"""

    def setup(self) -> None:
        """预置条件：用例前置准备，子类覆盖。"""

    def test_step(self) -> None:
        """测试步骤：核心用例逻辑，子类必须实现。"""
        raise NotImplementedError(f"{type(self).__name__} 未实现 test_step")

    def teardown(self) -> None:
        """恢复环境：测试后置清理，无论执行成功与否都会调用，子类覆盖。"""

    def run(self) -> None:
        """执行用例：setup -> test_step，teardown 无论成败必定执行。"""
        try:
            self.setup()
            self.test_step()
        finally:
            self.teardown()
