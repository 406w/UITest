# UITest 框架说明

基于 pytest + selenium/appium + allure 的测试框架
能够实现 Web、Android、IOS 系统的自动化测试

## 工程结构

```
UITest/
├── UITest.md                  # 本框架说明（规则文档）
├── pytest.ini                 # pytest 配置（--platform 切换 web/android/ios，--browser 切换浏览器）
├── conftest.py                # driver fixture + 失败自动截图
├── requirements.txt           # 依赖清单
├── page/                      # 页面层
│   ├── page_elements/         # ① 页面元素层（每个页面一个文件）
│   │   ├── locator.py         #    Page 基类 / 多系统适配 / 倒序引用
│   │   ├── bilibili_home_page.py
│   │   └── bilibili_login_page.py
│   ├── page_redirect/         # ② 页面跳转层（跳转来源声明 + ways_to 反查函数）
│   │   ├── login_page_redirects.py
│   │   └── home_page_redirects.py
│   └── page_objects/          # ③ 页面对象层（链式调用，暴露业务接口）
├── common/                    # 公共层
│   ├── base_operates.py       # BaseOperates 类 ④ 基础操作层（find 软等待/并行滚动、click 快照/弹窗截获、swipe 手势重构）
│   ├── driver.py              #    Driver 工厂（Web selenium / Android·IOS appium）
│   ├── base_test_case.py      #    用例基类（init/setup/test_step/teardown 框架）
│   └── business_flow.py       #    业务流程层（串联 PO 操作，复用业务场景）
├── data/                      # 测试基础数据（sqlite）
│   ├── test_data.db           #    sqlite 数据库（sites 站点表 + accounts 账号表，一网址多账号）
│   ├── database.py            #    DataBase 访问封装（get_sites/get_account/get_accounts/get_default_account）
│   └── init_db.py             #    数据库初始化脚本（幂等，可重复执行）
├── testcase/                  # 测试用例层
│   ├── test_bilibili_login.py
│   └── test_bilibili_login_scenario.py
└── report/                    # 测试报告
    ├── allure-results/        #    原始结果（pytest --alluredir 生成）
    └── allure-report/         #    HTML 报告（allure generate 生成）
```

## 分层规则

### 1、页面元素层（page/page_elements）

能力：每个页面一个 Page 类，声明页面控件定位器；支持多系统（web / android / ios）各自适配；无特征属性的控件通过"关系"（relation）定位；定位器倒序引用。

示例

```python
class HomePage(Page):
    class account:
        """账号按钮"""
        element_name = "账号"

        class web:
            id = "btn-account"

        class android:
            id = "com.example:id/btn_account"

        class ios:
            xpath = "//XCUIElementTypeButton[@name='账号']"
```

### 2、页面跳转层（page/page_redirect）

能力：声明页面间的跳转来源（ComeFrom），并提供 ways_to 反查"能跳转到目标页面的全部方式"，编码时直接查代码即可，无需打开实际页面。

示例

```python
class HomePage:
    class ComeFrom:
        """谁可以跳转到首页"""
        from_login_back = (BilibiliLoginPage, BilibiliLoginPage.back_btn)
```

### 3、基础操作层（common/base_operates.py）

能力：基础操作重构——find 软等待查找（可并行滚动辅助）、click 快照对比 + 弹窗截获、swipe 手势化滑动。

### 4、控制器（common/driver.py）

能力：统一创建 Web(selenium) / Android·IOS(appium) 驱动，通过 `--platform` / `--browser` 切换，用例不关心驱动创建。

### 5、用例脚本结构化（common/base_test_case.py）

能力：用例抽象成类，统一 `init -> setup -> test_step -> teardown` 结构，`run()` 保证 teardown 必定执行。

### 6、业务流程层（common/business_flow.py）

能力：串联各 PO 操作成可复用的业务场景（如"登录"流程），用例只调用业务流，不直接接触 PO 细节。

示例

```python
class BilibiliLoginFlow(BusinessFlow):
    def login(self, username, password):
        return (self.open_home()
                .ensure_not_logged_in()
                .go_to_login_page()
                .fill_login_form(username, password)
                .submit_login())

# 用例中直接调用
class TestLogin(TestCaseBase):
    def test_step(self):
        self.flow.login(user, pwd)
```

### 7、页面对象层（page/page_objects）

能力：实现页面全部控件操作，暴露业务接口，链式调用。

### 8、测试用例层（testcase）

能力：一个业务场景一个用例；通过 PageObject / 业务流程层组织操作，用例中不直接接触定位器；断言与业务步骤分离；标记 web / android / ios 按端运行。

示例

```python
@allure.title("完整登录流程")
def test_bilibili_complete_login_flow(driver):
    TestBilibiliCompleteLoginFlow(driver).run()
```

### 9、测试基础数据（data）

能力：sqlite 本地数据库存放站点与账号密码数据，用例通过 DataBase 读取，不硬编码账号密码。
