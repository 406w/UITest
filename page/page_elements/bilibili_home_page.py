"""哔哩哔哩首页页面元素声明（PageElement 层，嵌套类方式）。"""
from page.page_elements import Page, RelationType, jump


class BilibiliHomePage(Page):
    url = "https://www.bilibili.com/"
    desc = "哔哩哔哩首页"

    class home_header:
        """顶部导航栏"""
        element_name = "顶部导航栏"

        class web:
            css_selector = "div.bili-header"

        class android:
            id = "header"

        class ios:
            xpath = "//XCUIElementTypeOther[@name='header']"

    @jump("BilibiliLoginPage", desc="未登录入口链接跳转登录页")
    class login_entry:
        """未登录入口链接 - 有明确特征的控件"""
        element_name = "未登录入口链接"

        class web:
            text = "未登录"
            css_selector = "a.header-login-entry"

        class android:
            text = "未登录"
            id = "login_entry"

        class ios:
            text = "未登录"
            id = "loginEntry"
            xpath = "//XCUIElementTypeLink[@name='未登录']"

    @jump("BilibiliLoginPage", desc="登录按钮跳转登录页")
    class go_login_btn:
        """登录按钮 - 未登录态"""
        element_name = "登录按钮"

        class web:
            text = "登录"
            css_selector = "div.go-login-btn"

        class android:
            text = "登录"
            id = "go_login_btn"

        class ios:
            text = "登录"
            id = "goLoginBtn"
            xpath = "//XCUIElementTypeButton[@name='登录']"

    class account:
        """账号按钮 - 有明确特征的控件"""
        element_name = "账号"

        class android:
            text = "账号"
            id = "com.bilibili.app:id/btn_account"
            xpath = "//*[@text='账号']"

        class ios:
            text = "账号"
            id = "accountButton"
            xpath = "//XCUIElementTypeButton[@name='账号']"

        class web:
            text = "账号"
            id = "btn-account"
            css_selector = "#btn-account"

    class avatar:
        """头像 - 登录后头像图片（无文本无 ID，以图片地址特征定位）"""
        element_name = "头像"

        class android:
            class_name = "android.widget.ImageView"

            relation = {
                "type": RelationType.CHILD_OF,
                "parent": "home_header",
                "index": 0,
            }

        class ios:
            class_name = "XCUIElementTypeImage"

            relation = {
                "type": RelationType.CHILD_OF,
                "parent": "home_header",
                "index": 0,
            }

        class web:
            xpath = "//div.bili-header//img[contains(@src, 'hdslb.com/bfs')]"

    class nickname:
        """用户昵称 - 我的页/个人中心展示的用户昵称文本"""
        element_name = "用户昵称"

        class android:
            id = "com.bilibili.app:id/nickname"

        class ios:
            id = "nickname"
            xpath = "//XCUIElementTypeStaticText[@name='nickname']"

        class web:
            xpath = "//div.user-nickname|//div[contains(@class,'nickname')]"
