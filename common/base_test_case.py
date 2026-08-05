"""用例层基类：测试用例脚本框架。

用例类标准结构：
- __init__(driver): init，初始化测试用例，引入资源文件，实例化操作对象
- setup():        预置条件
- test_step():    测试步骤（子类必须实现）
- teardown():     恢复环境（无论执行成功与否都会执行）

执行入口 run()：setup -> test_step，teardown 在 finally 中必定执行。

多设备支持：传入 conftest 的 driver_manager 后，可在用例内通过
new_driver() 创建附加驱动（多个 web 页面 / 移动设备），用例结束自动关闭。
"""
from __future__ import annotations

import allure


def step(name: str) -> None:
    """操作步骤：在 allure 报告中记录一个操作步骤节点，并输出到控制台。

    关键字风格用法——step("XXX") 后紧跟该步骤的操作代码：
        step("打开哔哩哔哩首页")
        self.flow.open_home()

    等价于 `with allure.step(name): ...`，报告层级以步骤为节点。
    """
    with allure.step(name):
        print(f"[STEP] {name}")


def checkPoint(name: str, condition: bool = True, msg: str = "") -> None:
    """检查点（断言）：在 allure 报告中记录检查点节点并校验。

    用法：
        checkPoint("登录成功", self.flow.home.is_logged_in())
        checkPoint("登录成功", self.flow.home.is_logged_in(), "点击登录后应处于已登录状态")
        checkPoint("登录成功")          # 仅记录检查点，不校验（condition 默认 True）

    校验失败抛 AssertionError（pytest 标记失败），失败信息包含检查点名称；
    用例失败时 conftest 自动截图，与报告步骤共同构成检查点证据。
    """
    with allure.step(f"检查点：{name}"):
        if not condition:
            raise AssertionError(msg or f"检查点 [{name}] 未通过")
        print(f"[CHECKPOINT] {name} PASS")


class TestCaseBase:
    __test__ = False  # 标记非 pytest 测试类，由函数包装调用 run()

    def __init__(self, driver, platform: str = "web", driver_manager=None):
        """init：初始化测试用例。driver 由 conftest fixture 注入。

        driver_manager: 可选，传入 conftest 的 driver_manager fixture，
            用于在用例中创建/获取附加驱动（多页面、多设备）。
        """
        self.driver = driver
        self.platform = platform
        self.driver_manager = driver_manager
        self._extra_drivers: list[str] = []
        self._init_objects()

    # ---------------- 多设备控制 ----------------
    def new_driver(self, name: str, platform: str = "web", browser: str = "edge", **kwargs):
        """创建附加驱动（新 web 页面 / 移动设备），返回该 driver，用例中可直接控制。"""
        if self.driver_manager is None:
            raise RuntimeError(
                "未注入 driver_manager：用例入口需同时请求 driver_manager fixture，"
                "并在初始化时传入 TestCaseBase(driver, driver_manager=driver_manager)"
            )
        driver = self.driver_manager.create_driver(name, platform=platform, browser=browser, **kwargs)
        self._extra_drivers.append(name)
        return driver

    def get_driver(self, name: str = "main"):
        """获取已创建的驱动（默认主 driver）。"""
        if self.driver_manager is None:
            raise RuntimeError("未注入 driver_manager，无法获取其他驱动")
        return self.driver_manager.get_driver(name)

    def close_driver(self, name: str) -> None:
        """手动关闭指定驱动（主 driver 与附加驱动均可）。"""
        if self.driver_manager is None:
            raise RuntimeError("未注入 driver_manager，无法关闭驱动")
        self.driver_manager.close_driver(name)
        if name in self._extra_drivers:
            self._extra_drivers.remove(name)

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
        """执行用例：setup -> test_step，teardown 无论成败必定执行，最后自动关闭附加驱动。"""
        try:
            self.setup()
            self.test_step()
        finally:
            try:
                self.teardown()
            finally:
                self._close_extra_drivers()

    def _close_extra_drivers(self) -> None:
        """关闭用例内创建的附加驱动（主 driver 由 conftest 的 driver_manager fixture 统一关闭）。"""
        if self.driver_manager is None:
            return
        for name in list(self._extra_drivers):
            self.driver_manager.close_driver(name)
        self._extra_drivers.clear()
