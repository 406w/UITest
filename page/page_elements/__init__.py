import sys

from .locator import (
    ElementResolver,
    Page,
    PageMeta,
    RelationType,
    is_element_class,
    jump,
)
from .bilibili_home_page import BilibiliHomePage
from .bilibili_login_page import BilibiliLoginPage

# 页面命名空间：所有页面类集中于此，供 jump 跳转声明互相反查
PageElements = sys.modules[__name__]

__all__ = [
    "ElementResolver",
    "Page",
    "PageMeta",
    "RelationType",
    "is_element_class",
    "jump",
    "PageElements",
    "BilibiliHomePage",
    "BilibiliLoginPage",
]
