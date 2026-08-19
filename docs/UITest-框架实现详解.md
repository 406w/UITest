# UITest 自动化测试框架实现详解

> 基于 pytest + selenium/appium + allure 的多端 UI 自动化测试框架
> 支持 Web / Android / iOS 三端，支持一个用例同时控制多个 web 页面 / 移动设备

---

## 一、框架总览

### 1.1 技术栈

| 组件 | 用途 |
| --- | --- |
| pytest | 测试执行引擎、用例收集、命令行参数（--platform / --browser） |
| selenium | Web 端驱动（chrome / edge / firefox） |
| appium | Android / iOS 端驱动 |
| allure | 测试报告（步骤、截图、附件） |
| sqlite | 测试基础数据（站点表 + 账号表） |

### 1.2 分层架构

```
testcase（测试用例层：一个业务场景一个用例）
   │  调用
common/business_flow（业务流程层：串联 PO 形成业务场景）
   │  调用
page/page_objects（页面对象层：页面全部控件操作，链式调用）
   │  调用
common/base_operates（基础操作层：find/click/swipe 重构）
   │  使用
page/page_elements（页面元素层：控件定位器声明 + jump 跳转声明）
   │  注入
common/driver（控制器：Driver 工厂 + DriverManager 多设备管理）
   │  提供
conftest.py（driver/driver_manager fixture + 失败截图）
```

自下而上的依赖方向：**元素层 → 操作层 → 对象层 → 业务流层 → 用例层**，上层只依赖下层的公开接口，每层职责单一。

---

## 二、工程结构

```
UITest/
├── UITest.md                  # 框架说明（规则文档）
├── pytest.ini                 # pytest 配置（testpaths=testcase、pythonpath=.)
├── conftest.py                # driver fixture + 失败自动截图
├── requirements.txt           # 依赖清单
├── page/                      # 页面层
│   ├── page_elements/         # ① 页面元素层
│   │   ├── locator.py         #    Page 元类 / jump 跳转装饰器 / 关系解析 / 倒序引用
│   │   ├── bilibili_home_page.py
│   │   └── bilibili_login_page.py
│   └── page_objects/          # ② 页面对象层
│       ├── page_object.py     #    PageObject 基类
│       ├── bilibili_home_page_object.py
│       └── bilibili_login_page_object.py
├── common/                    # 公共层
│   ├── base_operates.py       # ④ 基础操作层（BaseOperates）
│   ├── driver.py              #    Driver 工厂 + DriverManager
│   ├── base_test_case.py      #    用例基类（TestCaseBase）
│   └── business_flow.py       #    业务流程层（BusinessFlow）
├── data/                      # 测试基础数据
│   ├── test_data.db           #    sqlite 数据库
│   ├── database.py            #    DataBase 访问封装
│   └── init_db.py             #    初始化脚本（幂等）
├── testcase/                  # 测试用例层
│   ├── test_bilibili_login.py
│   └── test_bilibili_login_scenario.py
└── report/                    # 测试报告（allure）
```

---

## 三、各层实现详解

### 3.1 页面元素层（page/page_elements）

**核心设计**：每个页面一个 Page 类，页面内每个控件是一个嵌套类，控件类统一声明 `element_name` + `web/android/ios` 平台子类。

#### PageMeta 元类（locator.py:44）

页面类的元类，类创建时自动完成：

1. **识别控件并倒序绑定**：遍历类属性，`is_element_class()`（包含 `element_name` 且至少有一个平台子类的类）判定为控件声明，自动为控件写入 `name`（属性名）和 `page`（所属页面类）——这就是"定位器.页面"的倒序引用，控件知道自己属于哪个页面。

2. **收集 jump 跳转声明**：控件上的 `jump` 装饰器写入 `_jump_to`（目标页面类名字符串）与 `_jump_desc`，查询时由 `Page.ways_to()` 统一反查。

#### Page 基类

- `ways_to(target_page)`：倒序反查，输出全部能跳转到目标页面的方式 `[(描述, 来源页面类, 来源控件类), ...]`
- `ways_from(source_page)`：正序，来源页面能跳到哪里
- `print_ways_to()`：格式化输出，方便排错
- `get_element()` / `element_names()`：按名称获取控件声明（支持父类继承），供操作层"自动获取类中对应属性"

#### ElementResolver 元素解析器

控件声明 → 实际定位器的转换中枢：

- **属性定位**：按平台优先级自动选定位方式。web 端 `css_selector > id > xpath > tag_name > text > name`；app 端 `id > xpath > text > class_name > ...`。`text` 特殊处理：web 转 `contains(normalize-space(text()))` 模糊匹配，app 转 `@text/@label` 匹配。
- **关系定位**（relation 字典）：`CHILD_OF` / `INSIDE` 通过 DOM 结构解析（取父控件子节点/后代），`ABOVE/BELOW/LEFT_OF/RIGHT_OF` 通过坐标法解析（web 用 JS 一次性取全部可见元素矩形，app 遍历元素 rect），按相对位置排序取第 index 个。
- **软等待**：属性定位与关系定位最终都走 WebDriverWait。

#### PageElements 命名空间

`page/page_elements/__init__.py` 将 `sys.modules[__name__]` 暴露为 `PageElements`，所有页面类集中于此，供 `jump` 跳转声明互相反查，避免循环导入。

### 3.2 页面跳转声明（PE 层 `jump` 装饰器）

**核心设计**：跳转关系直接声明在页面元素层——控件上用 `jump` 装饰器标注"能跳转到哪个页面"，编码时查代码即可，无需打开页面。不设独立跳转层（PR 层已移除）。

- **声明方式**：控件类上加 `@jump("目标页面类名", desc="跳转描述")`，目标页面以字符串类名引用（避免页面模块互相导入造成循环依赖）。
- **反查机制**：`Page._all_pages()` 遍历 `PageElements` 命名空间收集全部页面类，`Page.ways_to(目标页面)` 扫描各页面 `_jump_entries()`（带 `_jump_to` 的控件）匹配目标类名。
- **查询入口**（Page 基类类方法）：
  - `ways_to(目标页面)`：倒序反查，输出全部能跳转到目标页面的方式
  - `ways_from(来源页面)`：正序，来源页面能跳到哪里
  - `print_ways_to()`：格式化输出，方便排错

**PO 层应用**：`go_to_login()` 遍历 `ways_to(LoginPage)`，依次尝试点击各来源控件，第一个可点即跳转——页面跳转完全由声明驱动，新增跳转方式无需改 PO。

### 3.3 页面对象层（page/page_objects）

**核心设计**：一个页面一个 PO 类，实现该页面全部控件的全部操作，对外暴露业务接口，链式调用。

- **PageObject 基类**：持有 `page`（元素声明类）与 `operates`（BaseOperates 实例），提供 `open / find / find_all / send_keys / click / swipe / current_url / page_title / screenshot` 等代理方法——PO 层不用关心定位细节，只写业务语义。
- **具体 PO**（如 BilibiliHomePageObject）：
  - 页面操作：`open_home()`、`wait_loaded()`（等待页面特征控件出现）
  - 页面跳转：`go_to_login()` 基于 PE 层 jump 声明驱动
  - 业务接口：`is_logged_in()`（DOM 信号优先、cookie 兜底）、`login_status()`
  - 报告辅助：`attach_screenshot()` / `attach_text()` 直接写入 allure
- **链式调用**：每个操作返回 self，业务流与用例中可以一行串联多个操作。

### 3.4 基础操作层（common/base_operates.py）

对 selenium/appium 原始 API 的三类重构，是本框架操作稳定性的核心。

#### find 方法重构

- 多个查找函数：`find`（单元素）、`find_all`（多元素）、`find_by_text`（按文本模糊查找）
- 自动获取控件声明（`page.get_element(name)`），关系定位控件自动走 ElementResolver 并软等待重试
- **第二线程并行滚动**：`scroll=True` 时，主线程等待 + 后台线程边滚动边查找（`threading.Event` 通知找到即停），解决长页面控件不在视口的问题

#### click 方法重构

- **快照对比**：点击前后记录 url / title，点击结果以 `ClickResult` 对象返回（`url_changed` / `title_changed` / `popup_handled`）
- **弹窗截获**：点击后按 `POPUP_SELECTORS`（layui-layer / dialog / modal / toast 等）检测弹窗；web 端用 JS 校验"覆盖面积 ≥ 视口 10% 且中心在视口内"排除底部小提示条
- **弹窗处理策略**：允许传入 `popup_handler(popup_element, popup_text) -> bool`；返回 False 或未传 handler 时抛 `PopupError` 给出弹窗实际文本——预期外弹窗立即失败，而不是带病执行
- **预期校验**：`expected="url"/"title"` 断言点击后的跳转结果
- **真实手势兜底**：元素被遮挡点击失败时，用 ActionChains 移过去点

#### swipe 方法重构

- **web**：JS `scrollBy` 滚动，检测到滚动量 < 1px（到达边界）时反向补偿 40px 防反弹
- **app**：按窗口尺寸计算手势起止点（上滑 0.8h→0.2h），swipe 失败时 TouchActions 兜底
- 滑动距离默认视口 70%，自动适配屏幕

### 3.5 控制器（common/driver.py）

#### WebDriverFactory 驱动工厂

- `WebDriverFactory(platform, browser).create()` 统一创建三端驱动
- **web**：edge（默认）/ chrome / firefox，支持 `headless=True`，驱动由 webdriver_manager 自动下载管理，窗口默认最大化
- **android / ios**：appium Remote，automationName 自动匹配（UiAutomator2 / XCUITest），支持自定义 `appium_server` 与 `desired_capabilities`
- 非法平台抛 `UnsupportedPlatformError`，报错信息列出可选值

#### DriverManager 多设备管理

支持"一个用例控制多个 web 页面 / 移动设备"：

- `create_driver(name, platform, browser, **kwargs)`：创建并注册驱动（重名报错），统一设置页面加载超时
- `get_driver(name)` / `close_driver(name)` / `close_all()`
- `drivers` 属性返回存活驱动字典 `{名称: driver}`
- 支持 `with DriverManager() as m:` 上下文管理

### 3.6 用例基类（common/base_test_case.py）

**核心设计**：用例文件抽象成类，统一生命周期，文件底部用 pytest 函数包装。

- `__test__ = False`：标记非 pytest 测试类，防止 pytest 误收集
- 统一结构：
  - `__init__(driver, platform)` → `_init_objects()`：初始化，引入资源文件（data/PO/业务流）并实例化
  - `setup()`：预置条件
  - `test_step()`：测试步骤（子类必须实现）
  - `teardown()`：恢复环境
- `run()`：`setup -> test_step`，`teardown` 在 finally 中必定执行；最后自动关闭用例内创建的附加驱动
- **多设备支持**：传入 `driver_manager` 后可用 `new_driver()` 创建附加驱动、`get_driver()` 按名获取、`close_driver()` 手动关闭；附加驱动在 run() 结束时自动清理，主驱动由 conftest fixture 统一关闭

### 3.7 业务流程层（common/business_flow.py）

**核心设计**：把"多个 PO 操作串成一个业务场景"沉淀为可复用类，用例只调业务流。

- `BusinessFlow` 基类：持有 driver/platform，`_init_objects()` 实例化涉及的 PO 与数据源
- `BilibiliLoginFlow`：
  - 分步方法：`open_home` → `ensure_not_logged_in`（已登录则 pytest.skip）→ `go_to_login_page` → `fill_login_form` → `submit_login(verify=True)`
  - 完整流程 `login(username, password)`：链式串联全部步骤
  - 每一步用 `with allure.step(...)` 组织，allure 报告直接呈现业务步骤
- 步骤内给出明确失败原因（如"data 中未找到账号"、"未处于已登录状态，可能遇到验证码"）

### 3.8 测试基础数据（data）

- **sqlite 表结构**：`sites`（站点：name/url）+ `accounts`（账号密码：site_id/username/password/is_default），一个站点多个账号
- **DataBase 访问封装**：`get_sites / get_site / get_accounts / get_default_account / get_account(按指定账号取密码)`
- **init_db.py 初始化**：幂等脚本（重复执行不重复插入），新增站点/账号直接改 `INIT_SITES` / `INIT_ACCOUNTS` 后执行
- 用例通过 DataBase 读数据，**账号密码不硬编码在用例中**

### 3.9 测试用例层（testcase）

- 一个业务场景一个用例类，pytest 入口函数只做装饰 + 调用 `用例类(driver).run()`
- 现有用例：
  - `test_bilibili_login.py`：首页登录状态检查、按跳转关系进入登录页
  - `test_bilibili_login_scenario.py`：从 data 取账号输入登录表单（不提交）、完整登录流程（业务流 login() 驱动，含提交后验证）

### 3.10 全局配置（conftest.py）

- **命令行参数**：`--platform`（web/android/ios，默认 web）、`--browser`（edge/chrome/firefox，默认 edge）
- **fixture**：
  - `driver_manager`：function 作用域，测试结束 `close_all()` 统一清理
  - `driver`：由 manager 创建主驱动（名 main），平台/浏览器来自命令行参数
- **失败自动截图**：`pytest_runtest_makereport` hook 在用例失败时把截图 attach 到 allure；无主 driver 的用例取 manager 中任一存活驱动兜底

---

## 四、一次用例的完整执行流程

```
pytest 收集用例（testpaths=testcase）
  → driver_manager fixture 创建（空 DriverManager）
  → driver fixture 创建主驱动（--platform/--browser）
  → pytest 入口函数执行 用例类(driver, driver_manager=...).run()
      ├── __init__ → _init_objects：实例化 PO / 业务流 / 数据源
      ├── setup：预置条件（取账号、打开页面、确认未登录）
      ├── test_step：调用业务流方法（allure.step 记录每一步）
      ├── teardown：恢复环境（finally 保证）
      └── 关闭用例内附加驱动
  → 用例结束：driver_manager fixture 收尾 close_all()（主驱动 + 所有附加驱动退出）
  → 失败时：conftest 截图 attach 到 allure
  → 结果写入 report/allure-results（pytest.ini 的 addopts）
```

---

## 五、多设备 / 多页面控制

```python
# 用例入口同时请求 driver 与 driver_manager
def test_multi_device(driver, driver_manager):
    TestX(driver, driver_manager=driver_manager).run()

# 用例类中创建附加设备
class TestX(TestCaseBase):
    def _init_objects(self):
        self.home = BilibiliHomePageObject(self.driver)          # 主设备
        self.home2 = BilibiliHomePageObject(self.new_driver("page2", browser="chrome"))  # 附加页面
        self.android = self.new_driver("android-device", platform="android")             # 附加移动设备

    def test_step(self):
        self.home.open_home().wait_loaded()
        self.home2.open_home().wait_loaded()   # 同一用例内同时控制两个页面
```

- 主驱动与附加驱动都由 DriverManager 按名管理，互不干扰
- 附加驱动在 run() 结束时自动关闭，主驱动由 fixture 统一关闭，无需手动清理

---

## 六、运行方式

```bash
# 运行全部用例（默认 web + edge）
pytest

# 指定浏览器 / 平台
pytest --browser chrome
pytest --platform android

# 指定用例文件
pytest testcase/test_bilibili_login_scenario.py

# 生成并打开 HTML 报告
allure generate report/allure-results -o report/allure-report --clean
allure open report/allure-report

# 初始化测试数据
python data/init_db.py
```

---

## 七、扩展指引

| 需求 | 操作 |
| --- | --- |
| 新增页面 | page_elements 建 Page 类声明控件（控件上加 @jump 声明跳转）→ page_objects 建 PO 实现操作 |
| 新增业务场景 | common/business_flow 中新增业务流方法（复用现有分步）→ testcase 中建用例类 |
| 新增测试数据 | 修改 data/init_db.py 的 INIT_SITES / INIT_ACCOUNTS，执行 `python data/init_db.py` |
| 新设备进用例 | 用例入口加 driver_manager fixture，`self.new_driver(...)` 创建 |
| 新平台控件 | 控件类下新增对应平台子类（web/android/ios）声明定位属性即可 |
