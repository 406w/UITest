"""PageRedirect 层：页面跳转关系查询。

规则：
1. 页面跳转来源在页面类中通过 ComeFrom 声明（谁可以跳转到本页面）
2. 声明格式：来源描述 = (来源页面类, 来源页面控件类)，只声明 to_page（本页面），不定义 from_page 参数
3. 页面与 page_elements 中定义的页面保持一致，定位器从 page_elements 中引用
4. 引入关系函数，直接输出能跳转到目标页面的全部方式
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from page.page_elements import Page


class PageRedirect:
    """跳转关系查询入口：读取页面类 ComeFrom 声明，输出跳转关系。

    用法::

        PageRedirect.ways_to(LoginPage)          # [(来源描述, 来源页面类, 来源控件类), ...]
        PageRedirect.print_ways_to(LoginPage)    # 格式化输出全部跳转方式
    """

    @classmethod
    def ways_to(cls, target_page: type["Page"]) -> list[tuple[str, type["Page"], type]]:
        """倒序关联：输出所有能跳转到目标页面的方式。"""
        return target_page.come_from()

    @classmethod
    def ways_from(cls, source_page: type["Page"]) -> list[tuple[str, type["Page"], type]]:
        """正序关联：来源页面的控件能跳转到哪些页面。"""
        result = []
        for page in cls._all_pages():
            for desc, from_page, locator in page.come_from():
                if from_page is source_page:
                    result.append((desc, page, locator))
        return result

    @classmethod
    def print_ways_to(cls, target_page: type["Page"]) -> str:
        lines = [f"跳转到 {target_page.__name__} 的全部方式:"]
        for desc, from_page, locator in target_page.come_from():
            lines.append(
                f"  - {from_page.__name__} 页面的 {locator.name} 定位器"
                f"（{locator.element_name}）有能力跳转到 {target_page.__name__}"
                f"  [{desc}]"
            )
        return "\n".join(lines)

    @classmethod
    def _all_pages(cls) -> list[type["Page"]]:
        from page.page_elements import PageElements

        return [
            value
            for value in vars(PageElements).values()
            if isinstance(value, type) and issubclass(value, Page) and value is not Page
        ]
