"""PageElement 层：页面元素声明（嵌套类方式）。

规则：
1. 一个页面为一个 Page 类，页面内每个控件为一个嵌套类
2. 控件类统一声明方式：element_name + android/ios/web 平台子类
3. 无特征属性则用"关系"定位（relation 字典引用同页面其它控件）
4. 多系统适配：每个平台子类分别声明 text/id/xpath/css_selector/class_name/tag_name 等
5. 自动解析"关系"，转换为实际定位器
6. 控件倒序引用：引用方式从"页面.控件"，改为"控件.页面"
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


class PageMeta(type):
    """Page 元类：遍历嵌套类，识别控件声明并完成倒序绑定（控件.页面），
    解析 ComeFrom 跳转来源声明（只声明 to_page，来源以 (页面类, 控件类) 元组给出）。"""

    def __new__(mcs, name, bases, namespace):
        cls = super().__new__(mcs, name, bases, namespace)
        for attr_name, element_cls in namespace.items():
            if is_element_class(element_cls):
                element_cls.name = attr_name
                element_cls.page = cls
        mcs._bind_come_from(cls, namespace)
        return cls

    @staticmethod
    def _bind_come_from(cls, namespace):
        come_from = namespace.get("ComeFrom")
        if not isinstance(come_from, type):
            return
        entries = []
        for attr_name, value in vars(come_from).items():
            if attr_name.startswith("_"):
                continue
            if not (isinstance(value, tuple) and len(value) == 2):
                raise TypeError(
                    f"{cls.__name__}.ComeFrom.{attr_name} 声明格式错误，"
                    f"必须为 (来源页面类, 来源页面控件类)，当前为: {value!r}"
                )
            from_page_cls, locator = value
            if not (isinstance(from_page_cls, type) and issubclass(from_page_cls, Page)):
                raise TypeError(
                    f"{cls.__name__}.ComeFrom.{attr_name} 的来源必须引用 page_elements 中的 Page 子类，"
                    f"当前为: {from_page_cls!r}"
                )
            if not is_element_class(locator) or locator.page is not from_page_cls:
                raise ValueError(
                    f"{cls.__name__}.ComeFrom.{attr_name} 引用的控件 {locator!r} "
                    f"不属于来源页面 {from_page_cls.__name__}，请引用该页面中已声明的控件"
                )
            entries.append((attr_name, from_page_cls, locator))
        cls.ComeFromEntries = tuple(entries)


class Page(metaclass=PageMeta):
    """页面基类。一个页面一个 Page 类，统一声明页面控件。

    页面跳转来源声明：页面类内定义 ComeFrom 嵌套类，格式::

        class HomePage(Page):
            class ComeFrom:
                \"\"\"谁可以跳转到首页\"\"\"
                # 来源描述 = (来源页面类, 来源页面控件类)
                from_account_center_back = (AccountCenterPage, AccountCenterPage.back_btn)
    """

    url: str = ""
    desc: str = ""

    @classmethod
    def come_from(cls) -> list[tuple[str, type["Page"], type]]:
        """倒序关联：本页面能被谁跳转过来。返回 [(来源描述, 来源页面类, 来源控件类), ...]"""
        return list(getattr(cls, "ComeFromEntries", ()))

    @classmethod
    def define_come_from(cls, come_from_cls: type):
        """补充声明跳转来源（页面互相引用时，先定义页面再绑定 ComeFrom）。"""
        PageMeta._bind_come_from(cls, {"ComeFrom": come_from_cls})

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
