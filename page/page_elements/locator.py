"""PageElement 层：页面元素声明（嵌套类方式）与页面跳转声明（装饰器方式）。

规则：
1. 一个页面为一个 Page 类，页面内每个控件为一个嵌套类
2. 控件类统一声明方式：element_name + android/ios/web 平台子类
3. 无特征属性则用"关系"定位（relation 字典引用同页面其它控件）
4. 多系统适配：每个平台子类分别声明 text/id/xpath/css_selector/class_name/tag_name 等
5. 自动解析"关系"，转换为实际定位器
6. 控件倒序引用：引用方式从"页面.控件"，改为"控件.页面"
7. 页面跳转声明：控件上用 jump 装饰器声明"能跳转到哪个页面"，
   靠 Page 的 ways_to/ways_from 反查跳转关系，无需独立跳转层
"""
from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING

from selenium.webdriver.common.by import By

if TYPE_CHECKING:
    from selenium.webdriver.remote.webelement import WebElement

PLATFORMS = ("web", "android", "ios")


class RelationType(Enum):
    """关系定位类型。"""

    CHILD_OF = "child_of"      # parent 的子控件（配合 index 使用）
    INSIDE = "inside"          # parent 内部的后代元素
    ABOVE = "above"            # parent 的上方
    BELOW = "below"            # parent 的下方
    LEFT_OF = "left_of"        # parent 的左侧
    RIGHT_OF = "right_of"      # parent 的右侧


def is_element_class(obj) -> bool:
    """判断嵌套类是否为控件声明：包含 element_name 属性的类。"""
    return (
        isinstance(obj, type)
        and hasattr(obj, "element_name")
        and any(hasattr(obj, p) and isinstance(getattr(obj, p), type) for p in PLATFORMS)
    )


def jump(target: str, cond: str = "", desc: str = ""):
    """控件类装饰器：声明该控件有跳转到目标页面的能力（支持多条件分支）。

    用法::

        @jump("LoginPage", cond="未登录", desc="点击进入登录页")
        @jump("AccountCenterPage", cond="已登录", desc="点击进入个人中心")
        class account:
            ...

    同一个控件可叠加多个 @jump：不同条件下跳转到不同页面，用 cond 区分跳转分支；
    没有条件差异时可直接 @jump("LoginPage")（cond 为空表示无条件分支）。
    参数以字符串（目标页面类名）标注，避免页面模块互相导入造成循环依赖；
    目标页面类需在 page_elements 中定义并通过 PageElements 命名空间可查。
    """
    if not isinstance(target, str) or not target:
        raise TypeError("jump 的目标页面必须以字符串类名声明，例如 @jump(\"LoginPage\")")
    if cond is None:
        cond = ""

    def decorator(element_cls):
        jumps = getattr(element_cls, "_jump_targets", None)
        if jumps is None:
            jumps = []
            element_cls._jump_targets = jumps
        jumps.append((target, cond, desc or getattr(element_cls, "element_name", "")))
        return element_cls

    return decorator


class PageMeta(type):
    """Page 元类：遍历嵌套类，识别控件声明并完成倒序绑定（控件.页面），
    收集 jump 装饰器声明的跳转目标。"""

    def __new__(mcs, name, bases, namespace):
        cls = super().__new__(mcs, name, bases, namespace)
        for attr_name, element_cls in namespace.items():
            if is_element_class(element_cls):
                element_cls.name = attr_name
                element_cls.page = cls
        return cls


class Page(metaclass=PageMeta):
    """页面基类。一个页面一个 Page 类，统一声明页面控件。

    页面跳转声明：控件类上用 jump 装饰器标注目标页面（字符串类名），格式::

        class HomePage(Page):
            @jump("LoginPage", desc="点击进入登录页")
            class login_entry:
                ...

    url:          web 端页面地址（web 平台 open() 时 driver.get）
    package_name: Android 包名 / iOS BundleId（移动端 open() 时 activate_app），
                  web 平台留空
    main_activity: Android 主 Activity（移动端 open() 时 start_activity 强制回首页，
                  消除页面记忆；Android 平台必填，web/iOS 留空）
    """

    url: str = ""
    package_name: str = ""
    main_activity: str = ""
    desc: str = ""

    # ---------------- 跳转关系查询 ----------------
    @classmethod
    def _jump_entries(cls) -> list[tuple[str, str, str, type]]:
        """本页面内声明的全部跳转分支:
        [(目标页面类名, 跳转条件, 描述, 来源控件类), ...]"""
        entries = []
        for name, element_cls in vars(cls).items():
            jumps = getattr(element_cls, "_jump_targets", None) if is_element_class(element_cls) else None
            if not jumps:
                continue
            for target_name, cond, desc in jumps:
                entries.append((target_name, cond, desc, element_cls))
        return entries

    @classmethod
    def _all_pages(cls) -> list[type["Page"]]:
        from page.page_elements import PageElements

        return [
            value
            for value in vars(PageElements).values()
            if isinstance(value, type) and issubclass(value, Page) and value is not Page
        ]

    @classmethod
    def ways_to(
        cls,
        target_page: type["Page"],
        cond: str | None = None,
    ) -> list[tuple[str, str, type["Page"], type]]:
        """倒序关联：输出所有能跳转到目标页面的方式。
        返回 [(描述, 跳转条件, 来源页面类, 来源控件类), ...]；cond 非空时按条件过滤。"""
        result = []
        for page in cls._all_pages():
            for target_name, entry_cond, desc, locator in page._jump_entries():
                if target_name != target_page.__name__:
                    continue
                if cond is not None and entry_cond != cond:
                    continue
                result.append((desc, entry_cond, page, locator))
        return result

    @classmethod
    def ways_from(
        cls,
        source_page: type["Page"],
        cond: str | None = None,
    ) -> list[tuple[str, str, type["Page"], type]]:
        """正序关联：来源页面的控件能跳转到哪些页面。
        返回 [(描述, 跳转条件, 来源页面类, 来源控件类), ...]；cond 非空时按条件过滤。"""
        return source_page._jump_entries()

    @classmethod
    def print_ways_to(cls, target_page: type["Page"], cond: str | None = None) -> str:
        lines = [f"跳转到 {target_page.__name__} 的全部方式:"]
        for desc, entry_cond, from_page, locator in cls.ways_to(target_page, cond=cond):
            cond_tip = f",条件[{entry_cond}]" if entry_cond else ""
            lines.append(
                f"  - {from_page.__name__} 页面的 {locator.name} 定位器"
                f"（{locator.element_name}）有能力跳转到 {target_page.__name__}"
                f"{cond_tip}  [{desc}]"
            )
        return "\n".join(lines)

    @classmethod
    def element_names(cls) -> list[str]:
        return [
            name
            for name, value in vars(cls).items()
            if is_element_class(value)
        ]

    @classmethod
    def get_element(cls, name: str):
        """自动获取类中对应的控件声明。"""
        value = vars(cls).get(name)
        if is_element_class(value):
            return value
        for base in cls.__mro__[1:]:
            if issubclass(base, Page):
                value = vars(base).get(name)
                if is_element_class(value):
                    return value
        return None


class ElementResolver:
    """自动解析控件声明（含关系），转换为实际定位器/元素。"""

    # 各平台定位属性优先级
    _PRIORITY = {
        "web": ("css_selector", "id", "xpath", "tag_name", "text", "name"),
        "android": ("id", "xpath", "text", "class_name", "content_desc"),
        "ios": ("id", "xpath", "text", "class_name", "name"),
    }

    def __init__(self, platform: str = "web", timeout: float = 10.0):
        if platform not in PLATFORMS:
            raise ValueError(f"不支持的平台: {platform}，可选: {', '.join(PLATFORMS)}")
        self.platform = platform
        self.timeout = timeout

    def resolve(self, driver, element_cls) -> "WebElement":
        platform_cls = self._platform_cls(element_cls)
        relation = getattr(platform_cls, "relation", None)
        if relation:
            return self._resolve_relation(driver, element_cls, relation)
        return self._find_by_attributes(driver, element_cls)

    # ---------------- 属性定位 ----------------
    def locate_by(self, element_cls) -> tuple[str, str]:
        """按属性优先级自动生成 (By, value) 定位器。"""
        platform_cls = self._platform_cls(element_cls)
        for attr in self._PRIORITY[self.platform]:
            if not hasattr(platform_cls, attr):
                continue
            value = getattr(platform_cls, attr)
            if not isinstance(value, str) or not value:
                continue
            if self.platform == "web":
                if attr == "css_selector":
                    return By.CSS_SELECTOR, value
                if attr == "id":
                    return By.ID, value
                if attr == "xpath":
                    return By.XPATH, value
                if attr == "tag_name":
                    return By.TAG_NAME, value
                if attr == "text":
                    return By.XPATH, f"//*[contains(normalize-space(text()), '{value}')]"
                if attr == "name":
                    return By.NAME, value
            if attr == "id":
                return By.ID, value
            if attr == "xpath":
                return By.XPATH, value
            if attr == "text":
                return By.XPATH, f"//*[@text='{value}' or @label='{value}']"
            if attr == "class_name":
                return By.CLASS_NAME, value
            if attr == "content_desc":
                return By.XPATH, f"//*[@content-desc='{value}']"
            if attr == "name":
                return By.ID, value
        raise ValueError(
            f"控件 {element_cls.__name__} 未声明平台 {self.platform} 的定位属性，"
            f"可选属性: {', '.join(self._PRIORITY[self.platform])}"
        )

    def _find_by_attributes(self, driver, element_cls) -> "WebElement":
        by, value = self.locate_by(element_cls)
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.support.ui import WebDriverWait

        return WebDriverWait(driver, self.timeout).until(
            EC.presence_of_element_located((by, value))
        )

    # ---------------- 关系定位 ----------------
    def _resolve_relation(self, driver, element_cls, relation: dict) -> "WebElement":
        relation_type = relation.get("type")
        if not isinstance(relation_type, RelationType):
            raise ValueError(
                f"控件 {element_cls.__name__} 的 relation.type 必须是 RelationType 枚举，"
                f"当前为: {relation_type}"
            )
        parent_name = relation.get("parent")
        index = relation.get("index", 0)
        if parent_name is None:
            raise ValueError(f"控件 {element_cls.__name__} 的 relation 缺少 parent 引用")
        parent_cls = element_cls.page.get_element(parent_name)
        if parent_cls is None:
            raise ValueError(
                f"关系解析失败: 页面 {element_cls.page.__name__} 中找不到参照控件 {parent_name}"
            )
        parent_el = self.resolve(driver, parent_cls)

        if relation_type == RelationType.CHILD_OF:
            children = parent_el.find_elements(By.XPATH, "./*")
            if index >= len(children):
                raise AssertionError(
                    f"关系解析失败: {element_cls.page.__name__}.{element_cls.__name__} "
                    f"在 {parent_name} 下找不到第 {index} 个子控件（共 {len(children)} 个）"
                )
            return children[index]
        if relation_type == RelationType.INSIDE:
            descendants = parent_el.find_elements(By.XPATH, "./descendant::*")
            return descendants[index]
        return self._resolve_relation_by_position(driver, element_cls, parent_el, relation_type, index)

    def _resolve_relation_by_position(self, driver, element_cls, parent_el, relation_type: RelationType, index: int):
        """坐标法：above/below/left_of/right_of。"""
        from selenium.webdriver.remote.webelement import WebElement

        pr = parent_el.rect
        candidates = []
        if self.platform == "web":
            script = (
                "return Array.from(document.querySelectorAll('body *'))"
                ".filter(e => e.getClientRects().length > 0)"
                ".map(e => ({el: e, r: e.getBoundingClientRect()}))"
            )
            for node in driver.execute_script(script):
                r = node["r"]
                candidates.append((node["el"], r))
        else:
            for el in driver.find_elements(By.XPATH, "//*"):
                candidates.append((el, {"x": el.rect["x"], "y": el.rect["y"]}))

        def _rect(el_or_rect):
            if isinstance(el_or_rect, WebElement):
                r = el_or_rect.rect
                return r["x"], r["y"], r["width"], r["height"]
            r = el_or_rect
            return r["x"], r["y"], r["width"], r["height"]

        px, py, pw, ph = _rect(pr)
        matched = []
        for _el, r in candidates:
            x, y, w, h = _rect(r)
            if w <= 0 or h <= 0:
                continue
            if relation_type == RelationType.BELOW and y >= py + ph - 2:
                matched.append((y, _el))
            elif relation_type == RelationType.ABOVE and y + h <= py + 2:
                matched.append((-(y + h), _el))
            elif relation_type == RelationType.RIGHT_OF and x >= px + pw - 2:
                matched.append((x, _el))
            elif relation_type == RelationType.LEFT_OF and x + w <= px + 2:
                matched.append((-(x + w), _el))
        if not matched or index >= len(matched):
            raise AssertionError(
                f"关系解析失败: {element_cls.page.__name__}.{element_cls.__name__} "
                f"未找到 {relation_type.value} 于 {parent_el} 的第 {index} 个元素"
            )
        matched.sort(key=lambda item: item[0])
        return matched[index][1]

    # ---------------- 工具 ----------------
    def _platform_cls(self, element_cls):
        platform_cls = getattr(element_cls, self.platform, None)
        if not isinstance(platform_cls, type):
            raise ValueError(
                f"控件 {element_cls.__name__} 未声明平台 {self.platform} 的子类"
            )
        return platform_cls
