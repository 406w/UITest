"""测试用例层：文本用例 text_case.md → pytest 脚本（自动转换产物）。

源文件: G:\\Project\\UITest\\text_case.md
用例编号: BilibiliHomePageObject

源用例内容:
    预置步骤: 1. 打开手机  2. 打开哔哩哔哩应用
    测试步骤: 1. 点击我的  2. 点击头像
    预期结果: 2. 检查用户昵称是否为"励志成为雏生大王_406"

说明: 预置步骤中"打开手机/打开应用"由 conftest 的 driver fixture
(platform=android/ios + appium) 承担；本脚本仅保留业务步骤与检查点。
"""
# ---------------- 引入资源文件 ----------------
import allure
import pytest

from common.base_test_case import TestCaseBase, checkPoint, step
from page.page_objects.bilibili_home_page_object import BilibiliHomePageObject

# 预期昵称（源自 text_case.md 预期结果，如账号变化需同步更新）
EXPECTED_NICKNAME = "励志成为雏生大王_406"


class TestBilibiliMyNickname(TestCaseBase):
    """文本用例：点击我的 -> 点击头像 -> 校验昵称。"""

    __test__ = False  # 非 pytest 测试类，由下方函数入口调用 run()

    # ---------------- init：初始化测试用例 ----------------
    def _init_objects(self) -> None:
        self.home = BilibiliHomePageObject(self.driver, platform=self.platform)

    # ---------------- setup：预置条件（打开手机/打开App由driver承担） ----------------
    def setup(self) -> None:
        with allure.step("预置条件：打开哔哩哔哩应用并等待首页加载"):
            self.home.open_home().wait_loaded()
            if self.platform == "web":
                assert "哔哩哔哩" in self.home.page_title(), f"页面标题异常: {self.home.page_title()}"

    # ---------------- test_step：测试步骤 ----------------
    def test_step(self) -> None:
        step("点击我的")
        self.home.click_my()

        step("点击头像")
        self.home.click_avatar()
        self.home.attach_screenshot("my_page")

        # ---------------- 预期结果检查点 ----------------
        nickname = self.home.get_nickname()
        self.home.attach_text(f"实际昵称: {nickname}", name="actual_nickname")
        checkPoint("用户昵称为「励志成为雏生大王_406」", f"实际: {nickname}")
        assert nickname == EXPECTED_NICKNAME, f"昵称不符: 期望 {EXPECTED_NICKNAME}，实际 {nickname}"
        print(f"\n昵称校验通过: {nickname}")

    # ---------------- teardown：恢复环境 ----------------
    def teardown(self) -> None:
        pass


# ---------------- 用例入口（pytest 函数包装，teardown 由基类 run 保证必定执行） ----------------
@pytest.mark.ui
@pytest.mark.android
@pytest.mark.ios
@allure.feature("哔哩哔哩")
@allure.story("我的-昵称")
@allure.title("打开哔哩哔哩应用，点击我的-头像，校验用户昵称")
def test_bilibili_my_nickname(driver, platform_config):
    TestBilibiliMyNickname(driver, platform=platform_config).run()
