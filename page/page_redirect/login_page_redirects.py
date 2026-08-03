"""BilibiliLoginPage 跳转来源声明：谁可以跳转到登录页。

规则：
- 只声明 to_page（本页面），不定义 from_page 参数
- 格式：来源描述 = (来源页面类, 来源页面控件类)
- 页面与定位器从 page_elements 中引用
"""
from page.page_elements.bilibili_home_page import BilibiliHomePage
from page.page_elements.bilibili_login_page import BilibiliLoginPage


class LoginPageComeFrom:
    """谁可以跳转到登录页"""
    from_home_login_entry = (BilibiliHomePage, BilibiliHomePage.login_entry)
    from_home_go_login_btn = (BilibiliHomePage, BilibiliHomePage.go_login_btn)


BilibiliLoginPage.define_come_from(LoginPageComeFrom)
