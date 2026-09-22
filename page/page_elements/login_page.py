class LoginPage:
    class ready:
        """登录表单"""
        id = "login-form"

    class username:
        """用户名"""
        name = "username"
        attrs = {"data-testid": "login-username"}

    class password:
        """密码"""
        type = "password"
        attrs = {"data-testid": "login-password"}

    class submit:
        """登录工作台按钮"""
        tag = "button"
        attrs = {"data-testid": "login-submit"}

    class error:
        """登录错误提示"""
        id = "login-error"
