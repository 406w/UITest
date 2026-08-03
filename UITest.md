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
│   ├── base_operates/         # ④ 基础操作层（find 软等待/并行滚动、click 快照/弹窗截获、swipe 手势重构）
│   ├── driver/                #    Driver 工厂（Web selenium / Android·IOS appium）
│   └── testcase/              #    用例基类（init/setup/test_step/teardown 框架）
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

1. 一个页面为一个 Page 类
2. 定位器统一声明方式，不论有无特征属性
3. 无特征属性则"关系"同页面其它定位器
4. 多系统适配（web / android / ios 各自声明定位器）
    示例
    class HomePage:
        """首页"""
    
        class account:
            """账号按钮 - 有明确特征的控件"""
            element_name = "账号"
            
            class android:
                text = "账号"
                id = "com.example:id/btn_account"
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
            """头像 - 只是一个ImageView，没有文本也没有ID"""
            element_name = "头像"
            
            class android:
                # 基础属性（仅用于识别控件类型）
                class_name = "android.widget.ImageView"
                
                # 关系定位：通过父控件定位
                relation = {
                    "type": RelationType.CHILD_OF,
                    "parent": "home_header",  # 引用同页面的其他控件
                    "index": 0  # 父控件下的第0个子控件
                }
            
            class ios:
                class_name = "XCUIElementTypeImage"
                
                relation = {
                    "type": RelationType.CHILD_OF,
                    "parent": "home_header",
                    "index": 0
                }
            
            class web:
                tag_name = "img"
                
                relation = {
                    "type": RelationType.CHILD_OF,
                    "parent": "home_header",
                    "index": 0
                }
5. 自动解析"关系"，转换为实际定位器
6. 定位器倒序引用，引用方式从页面.定位器，改为定位器.页面

### 2、页面跳转层（page/page_redirect）

1. 引入页面跳转的关系，便于脚本编码时能直接从代码中查找页面跳转，不需要查看实际页面
2. 页面关系倒序关联
3. 引入关系函数，直接输出能跳转到目标页面的全部方式
4. 跳转来源（ComeFrom）在 page_redirect 层声明，每个页面一个声明文件，只声明 to_page（本页面），不定义 from_page 参数，格式：来源描述 = (来源页面类, 来源页面控件类)，页面与定位器从 page_elements 中引用
    示例
    class HomePage:
        """首页"""
        
        class ComeFrom:
            """谁可以跳转到首页"""
            # 格式：来源描述 = (页面类, 控件属性名)
            from_account_center_back = (
                PageElements.AccountCenterPage, 
                PageElements.AccountCenterPage.back_btn
            )
            from_security_back = (
                PageElements.SecurityPage,
                PageElements.SecurityPage.back_btn
            )

### 3、基础操作层（common/base_operates）

find 方法定位器查找
1. 声明不同函数对定位器不同属性的控件进行查找
2. 自动获取类中对应的属性
3. 软等待
4. 第二线程并行滚动，辅助查找

click 方法重构
1. 获取当前页面快照，对比操作后的实际结果
2. 允许传入处理指定弹窗的处理函数
3. 截获可能出现的弹窗，如果弹窗不是目标弹窗，给出实际报错原因

swipe 方法重构
1. 按照实际的手势操作进行
2. 处理控件只出现一部分的情况
3. 处理反弹问题

### 4、页面对象层（page/page_objects）

1. 关联 PageElement 层中的单个页面的 Page 类
2. 实现该页面全部控件的全部操作
3. 暴露业务需要用到的接口
4. 链式调用

### 5、测试用例层（testcase）

1. 一个业务场景为一个用例函数
2. 通过 PageObject 层组织操作，用例中不直接接触定位器
3. 断言与业务步骤分离，失败原因明确
4. 用例标记 web / android / ios，按端运行
5. 脚本框架：用例文件抽象成类，继承 common/testcase/base_test_case.py 的 TestCaseBase，
   类包含以下方法，统一结构：
   - `__init__(driver)` / `_init_objects()`: init，初始化测试用例，引入资源文件，实例化操作对象
   - `setup()`: 预置条件
   - `test_step()`: 测试步骤（子类必须实现）
   - `teardown()`: 恢复环境（无论执行成功与否都会执行）
   类内加 `__test__ = False` 标记非 pytest 测试类，文件底部提供 pytest 函数入口调用 `用例类(driver).run()`，
   run() 内部保证 setup -> test_step -> teardown(finally 必定执行)

### 6、测试基础数据（data）

1. sqlite 本地数据库 `data/test_data.db`，表 sites（站点）+ accounts（账号密码，一个网址对应多个账号）
2. 初始化脚本 `data/init_db.py`（幂等）：新增站点/账号直接修改 INIT_SITES / INIT_ACCOUNTS 后执行
3. 访问封装 `data/database.py`：get_sites / get_site / get_accounts / get_default_account / get_account(按指定账号取密码)
4. 用例通过 DataBase 读取测试数据，不在用例中硬编码账号密码
