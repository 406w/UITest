import sys

from .locator import (
    ElementResolver,
    Page,
    PageMeta,
    RelationType,
    is_element_class,
)
from .bilibili_home_page import BilibiliHomePage
from .bilibili_login_page import BilibiliLoginPage

# 页面命名空间：所有页面类集中于此，供 ComeFrom 跳转来源互相引用
PageElements = sys.modules[__name__]

__all__ = [
    "ElementResolver",
    "Page",
    "PageMeta",
    "RelationType",
    "is_element_class",
    "PageElements",
    "BilibiliHomePage",
    "BilibiliLoginPage",
]
