"""哔哩哔哩登录页页面元素声明（PageElement 层，嵌套类方式）。"""
from page.page_elements import Page, jump


class BilibiliLoginPage(Page):
    url = "https://passport.bilibili.com/login"
    desc = "哔哩哔哩登录页"

    @jump("BilibiliHomePage", desc="返回按钮跳回首页")
    class back_btn:
        """返回按钮"""
        element_name = "返回按钮"

        class web:
            css_selector = "div.backtohome"

        class android:
            id = "back_btn"

        class ios:
            xpath = "//XCUIElementTypeButton[@name='back']"

    class username:
        """账号输入框"""
        element_name = "账号输入框"

        class web:
            css_selector = "input[placeholder*='账号']"

        class android:
            id = "username"

        class ios:
            xpath = "//XCUIElementTypeTextField[@name='username']"

    class password:
        """密码输入框"""
        element_name = "密码输入框"

        class web:
            css_selector = "input[placeholder*='密码']"

        class android:
            id = "password"

        class ios:
            xpath = "//XCUIElementTypeSecureTextField[@name='password']"

    @jump("BilibiliHomePage", desc="登录成功后跳转首页")
    class login_btn:
        """登录按钮"""
        element_name = "登录按钮"

        class web:
            text = "登录"
            css_selector = "div.btn_primary"

        class android:
            text = "登录"
            id = "login_btn"

        class ios:
            text = "登录"
            id = "loginBtn"
            xpath = "//XCUIElementTypeButton[@name='登录']"
