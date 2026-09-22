class HomePage:
    class ready:
        """运营概览页面标题"""
        css = "#content h1"
        text = "运营概览"

    class user_menu:
        """当前用户名称，从顶栏头像的相邻元素获取"""

    class logout:
        """退出登录按钮"""
        tag = "button"
        attrs = {"data-action": "logout", "aria-label": "退出登录"}

    class sale:
        """销售管理菜单"""
        css = '.nav a[href="#/sale"]'

    class purchase:
        """采购管理菜单"""
        css = '.nav a[href="#/purchase"]'
