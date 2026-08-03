"""BilibiliHomePage 跳转来源声明：谁可以跳转到首页。

规则：
- 只声明 to_page（本页面），不定义 from_page 参数
- 格式：来源描述 = (来源页面类, 来源页面控件类)
- 页面与定位器从 page_elements 中引用
"""
from page.page_elements.bilibili_home_page import BilibiliHomePage
from page.page_elements.bilibili_login_page import BilibiliLoginPage


class HomePageComeFrom:
    """谁可以跳转到首页"""
    from_login_back = (BilibiliLoginPage, BilibiliLoginPage.back_btn)
    from_login_success = (BilibiliLoginPage, BilibiliLoginPage.login_btn)


BilibiliHomePage.define_come_from(HomePageComeFrom)
