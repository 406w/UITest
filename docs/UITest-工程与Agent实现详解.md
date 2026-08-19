# UITest 测试工程与配套 Agent 实现详解

> 文档日期：2026-08-06
> 覆盖范围：`G:\Project\UITest` 测试工程 + `G:\AI\.config\opencode\agent` 下 8 个 UITest 配套 Agent

---

## 目录

- [一、测试工程实现解读](#一测试工程实现解读)
  - [1.1 总体架构](#11-总体架构)
  - [1.2 页面元素层（PE）](#12-页面元素层pe)
  - [1.3 页面对象层（PO）](#13-页面对象层po)
  - [1.4 基础操作层（BaseOperates）](#14-基础操作层baseoperates)
  - [1.5 控制器层（Driver）](#15-控制器层driver)
  - [1.6 用例层（TestCaseBase）](#16-用例层testcasebase)
  - [1.7 业务流层（BusinessFlow）](#17-业务流层businessflow)
  - [1.8 数据层（data）](#18-数据层data)
  - [1.9 工程配置（conftest / pytest.ini）](#19-工程配置conftest--pytestini)
- [二、配套 Agent 实现解读](#二配套-agent-实现解读)
  - [2.1 编排者：uitest-pipeline](#21-编排者uitest-pipeline)
  - [2.2 子 Agent 全景表](#22-子-agent-全景表)
  - [2.3 各子 Agent 关键设计点](#23-各子-agent-关键设计点)
- [三、实战复盘（Android 真机）](#三实战复盘android-真机)
- [四、核心小结](#四核心小结)

---

# 一、测试工程实现解读

## 1.1 总体架构

工程根：`G:\Project\UITest`，基于 **pytest + selenium/appium + allure**，支持 Web / Android / iOS 三端。

```
UITest/
├── UITest.md                  # 框架规则文档
├── pytest.ini                 # pytest 配置（--platform 切换 web/android/ios）
├── conftest.py                # driver fixture + 失败自动截图 + 平台参数
├── requirements.txt           # 依赖清单
├── page/
│   ├── page_elements/         # ① 页面元素层（页面 + 控件 + 跳转声明）
│   │   ├── locator.py         #    Page 基类 / 多系统适配 / jump / ways_to / ElementResolver
│   │   ├── bilibili_home_page.py
│   │   └── bilibili_login_page.py
│   └── page_objects/          # ② 页面对象层（链式调用，暴露业务接口）
├── common/
│   ├── base_operates.py       # ③ 基础操作层（find/click/swipe 重构）
│   ├── driver.py              # ④ 控制器层（多端 Driver 工厂 + 多设备管理）
│   ├── base_test_case.py      # ⑤ 用例基类（init/setup/test_step/teardown）
│   └── business_flow.py       # ⑥ 业务流程层（串联 PO 操作）
├── data/                      # 测试基础数据（sqlite）
│   ├── test_data.db
│   ├── database.py            # DataBase 访问封装
│   └── init_db.py             # 数据库初始化（幂等）
├── testcase/                  # ⑦ 测试用例层
├── docs/                      # 文档（本文件 + UITest-框架实现详解.md）
└── report/                    # allure 报告
```

**核心设计哲学**：把「页面控件定位」与「页面操作逻辑」分离成 PE / PO 两层，再叠业务流层，用例只写业务步骤。这是从经典 POM 演化出的**四层职责分离**（PE → PO → Flow → TestCase）。

## 1.2 页面元素层（PE）

位置：`page/page_elements/`，核心文件 `locator.py`（框架灵魂，354 行）。

### Page 基类（locator.py:90）

```python
class Page(metaclass=PageMeta):
    url: str = ""                # web 端地址
    package_name: str = ""       # Android 包名 / iOS BundleId
    main_activity: str = ""      # Android 主 Activity（移动端 open() 冷启动回首页）
    desc: str = ""
```

### jump 装饰器（locator.py:46）

在控件类上声明「点击此控件可跳转到哪个页面」，目标以**字符串类名**引用避免循环导入：

```python
@jump("BilibiliLoginPage", desc="未登录入口链接跳转登录页")
class login_entry:
    ...
```

支持叠加多个 `@jump` + `cond` 条件分支（如未登录→登录页 / 已登录→个人中心）。

### PageMeta 元类（locator.py:77）

自动遍历嵌套类识别控件声明（有 `element_name` 且含 `web/android/ios` 平台子类即视为控件），并完成**倒序绑定**（`控件.page = 所属页面类`）。

### 跳转反查（locator.py:137）

- `Page.ways_to(目标页, cond=)`：反查「能跳转到目标页的全部方式」`[(描述, 条件, 来源页面类, 来源控件类)]`
- `Page.ways_from(来源页)`：正序查询
- `Page.print_ways_to()`：格式化输出

编码时**查码不查页面**——`go_to_login()` 就是遍历 `ways_to` 自动选择可用入口实现的。

### ElementResolver（locator.py:198）

按平台优先级解析定位器：

| 平台 | 定位属性优先级 |
|---|---|
| web | css_selector → id → xpath → tag_name → text → name |
| android | id → xpath → text → class_name → content_desc |
| ios | id → xpath → text → class_name → name |

text 在 Android 转 `//*[@text='x' or @label='x']`，content_desc 转 `//*[@content-desc='x']`。

### relation 关系定位

无特征属性的控件通过关系引用同页面其它控件：`CHILD_OF / INSIDE / ABOVE / BELOW / LEFT_OF / RIGHT_OF`，含 index 下标。

### 控件声明示例（bilibili_home_page.py）

```python
class BilibiliHomePage(Page):
    url = "https://www.bilibili.com/"
    package_name = "tv.danmaku.bili"
    main_activity = "tv.danmaku.bili.MainActivityV2"

    class account:                        # 「我的」入口
        class android:
            text = "我的"
            xpath = "//*[@text='我的']"
        class web:
            id = "btn-account"
            css_selector = "#btn-account"

    class avatar:                         # 头像（真机 id）
        class android:
            id = "tv.danmaku.bili:id/layer_avatar"

    class nickname:                       # 昵称（真机 id）
        class android:
            id = "tv.danmaku.bili:id/nick_name"
```

## 1.3 页面对象层（PO）

位置：`page/page_objects/`。

### PageObject 基类（page_object.py:19）

封装 `open / find / find_all / send_keys / click / swipe / current_url / page_title`。

**`open()` 移动端冷启动**（page_object.py:30）：

```python
if self.platform == "android" and package_name and main_activity:
    try:
        self.driver.terminate_app(package_name)   # 先杀进程
    except Exception:
        pass
    self.driver.activate_app(package_name)         # 再拉起 → 回到主 Activity
    return self
```

> 关键决策：App 有页面记忆（上次停哪页下次回哪页），`activate_app` 直接恢复旧页会导致脚本从错误页面开始。冷启动强制回到主 Activity 首页。
> 注：appium python client 5.x 已移除 `start_activity` 方法，故用 terminate + activate 替代。

### BilibiliHomePageObject（bilibili_home_page_object.py:19）

- `open_home()` → `open()`
- `wait_loaded()` → **以底部导航「我的」为加载标志**（关键：App 默认可能停在任意主 Tab 如直播/首页，`nav_top_bar` 只存在于首页推荐页，底部 5 tab 导航始终存在）
- `go_to_login()` → 遍历 `Page.ways_to(BilibiliLoginPage)` 自动选可用入口跳登录页
- `is_logged_in()` → 登录/未登录入口 DOM 信号优先 + cookie 兜底（20 次软轮询）
- `click_my() / click_avatar() / get_nickname()` → 对应文本用例动作

## 1.4 基础操作层（BaseOperates）

位置：`common/base_operates.py`（372 行），对原生 selenium/appium API 的三处重构。

### ① find 软等待 + 并行滚动（base_operates.py:87）

- 默认 `WebDriverWait + visibility_of_element_located`（等待可见）/ `presence_of_element_located`
- `scroll=True` 时开 **daemon 线程并行滚动**查找，主线程 join 超时兜底（长列表场景）

### ② click 快照对比 + 弹窗截获（base_operates.py:244）

```
before_snapshot(url+title) → 点击 → after_snapshot → url_changed/title_changed
→ _detect_popup() 弹窗检测 → popup_handler 处理 or 抛 PopupError
```

- 弹窗检测：匹配 `POPUP_SELECTORS`（div.layui-layer / dialog / modal / popup / toast / message / alert）；web 端 JS 判断「覆盖面积 ≥ 视口 10% 且中心在视口内」规避底部小提示条
- `popup_handler(popup_el, text) -> bool`：返回 True 表示预期弹窗已处理；False 或未传 → `PopupError`
- `expected="url"/"title"`：点击后校验跳转，失败抛 AssertionError

### ③ swipe 手势化（base_operates.py:312）

- web：JS `scrollBy` + **边界检测**（scrollY 无变化即到边界，反向回弹 40px）
- 移动端：标准手势坐标（起终点按屏占比），`driver.swipe` 失败回退 `TouchActions.flick`

## 1.5 控制器层（Driver）

位置：`common/driver.py`。

### WebDriverFactory（driver.py:21）

- `--platform` 决定 web（selenium Edge/Chrome/Firefox + webdriver_manager 自动装驱动）或 android/ios（appium Remote）
- **appium 5.x 兼容**（driver.py:99）：必须用 `options` 参数（`UiAutomator2Options` / `XCUITestOptions`），旧版「传 dict」方式已失效
- 超时设置分平台：web 端 `set_page_load_timeout`；移动端 `implicitly_wait(10)`（Appium 不支持 pageLoad timeout，会报 `Not implemented yet for pageLoad`）

### DriverManager（driver.py:129）

按 `name` 注册/获取/关闭多个 driver，一个用例可同时控制多个 web 页面 / 移动设备（`new_driver("page2", browser="chrome")`），用例结束 `close_all` 自动全部关闭。

## 1.6 用例层（TestCaseBase）

位置：`common/base_test_case.py`。

### step / checkPoint（base_test_case.py:19-46）

```python
def step(name: str) -> None:
    """操作步骤：allure 报告记录 + 控制台输出。"""

def checkPoint(name: str, actual: str = "") -> None:
    """检查点登记：仅登记文本用例预期结果，不实现断言。

    用法：
        nickname = self.home.get_nickname()
        checkPoint("用户昵称为「励志成为雏生大王_406」", f"实际: {nickname}")
        assert nickname == EXPECTED_NICKNAME, f"昵称不符: 期望 {EXPECTED_NICKNAME}，实际 {nickname}"
    """
```

> **重要约定（本次调整）**：`checkPoint` 只把「文本用例的预期结果」登记进 allure 报告（作为证据），**不做断言**；真正的校验由紧跟的原生 `assert` 完成。职责分离——checkPoint 负责记录，assert 负责判定。

### 用例类结构（base_test_case.py:49）

```
init → setup（预置条件） → test_step（核心，子类必须实现） → teardown（恢复环境）
```

- `run()`（base_test_case.py:103）：`try: setup → test_step`，`finally: teardown`（无论成败必定执行）+ 自动关闭附加驱动
- `new_driver(name, platform, browser)`：用例内创建附加驱动（多页面/多设备）
- `get_driver / close_driver`：按名获取 / 关闭

### pytest 入口（testcase 内）

```python
@pytest.mark.ui
@pytest.mark.android
@pytest.mark.ios
@allure.feature("哔哩哔哩")
@allure.story("我的-昵称")
@allure.title("打开哔哩哔哩应用，点击我的-头像，校验用户昵称")
def test_bilibili_my_nickname(driver, platform_config):
    TestBilibiliMyNickname(driver, platform=platform_config).run()
```

> **平台注入**：入口必须把 `platform_config`（来自 conftest 的 `--platform`）传入 TestCaseBase。默认 `platform="web"` 会导致 PO 全程用 web 定位器在原生 App 上查找而失败——这是本次实战的核心根因。

## 1.7 业务流层（BusinessFlow）

位置：`common/business_flow.py`。

```python
class BilibiliLoginFlow(BusinessFlow):
    def _init_objects(self):
        self.home = BilibiliHomePageObject(self.driver, platform=self.platform)
        self.login = BilibiliLoginPageObject(self.driver, platform=self.platform)
        self.db = DataBase()

    # 分步方法：open_home / ensure_not_logged_in / go_to_login_page /
    #          fill_login_form / submit_login，每步 allure.step + 链式返回 self

    # 完整流程：一行链式
    def login(self, username, password, verify=True):
        return (self.open_home()
                .ensure_not_logged_in()
                .go_to_login_page()
                .fill_login_form(username, password)
                .submit_login(verify=verify))
```

规则：分步方法动词小下划线命名 + 链式；数据从 DataBase 取不硬编码；用例只调业务流，不接触 PO 细节。

## 1.8 数据层（data）

sqlite 本地库（`test_data.db`）：`sites` 站点表 + `accounts` 账号表，一网址多账号。`DataBase` 提供 `get_sites / get_account / get_accounts / get_default_account`，`init_db.py` 幂等初始化。

## 1.9 工程配置（conftest / pytest.ini）

### conftest.py

| fixture | 作用 |
|---|---|
| `platform_config`（session） | 透传 `--platform`，供用例入口注入 TestCaseBase |
| `driver_manager`（function） | 多设备驱动管理，用例结束自动 close_all |
| `driver`（function） | 主 driver；android/ios 透传 `--udid/--app-package/--app-activity` 进 appium caps |
| `pytest_runtest_makereport` | 用例失败自动 allure 截图 `failure_screenshot` |

### pytest.ini

```
addopts = -v -s
testpaths = testcase
markers = ui / web / android / ios
```

---

# 一·五、重要函数接口实现逻辑

> 按「元素解析 → 定位 → 操作 → 用例执行」的调用链顺序，列出核心函数/接口的实现逻辑（签名 + 算法 + 关键决策点）。源码以本文件撰写时的工程状态为准。

## 1 PageMeta.__new__ —— 控件倒序绑定

```python
def __new__(mcs, name, bases, namespace):
    cls = super().__new__(mcs, name, bases, namespace)
    for attr_name, element_cls in namespace.items():
        if is_element_class(element_cls):     # 有 element_name 且含 web/android/ios 子类
            element_cls.name = attr_name       # 控件.name = 类属性名
            element_cls.page = cls              # 控件.page = 所属 Page 类
    return cls
```

**实现逻辑**：每个 Page 类创建时，元类扫描其直接定义的嵌套类，凡是满足 `is_element_class`（有 `element_name` 且至少一个平台子类）即视为控件，注入 `name`（用于 `find("控件名")` 索引）与 `page`（用于 relation 反查同页面其它控件）。这使控件类在编译期自动挂到页面上，运行期查找零开销。

## 2 jump 装饰器 + _jump_entries —— 跳转声明与反查（locator.py:46 / :114）

```python
def jump(target: str, cond: str = "", desc: str = ""):
    def decorator(element_cls):
        jumps = getattr(element_cls, "_jump_targets", None) or []
        jumps.append((target, cond, desc or getattr(element_cls, "element_name", "")))
        element_cls._jump_targets = jumps      # (_jump_targets 挂在控件类上)
        return element_cls
    return decorator

# Page._jump_entries(cls):
#    遍历本页面所有控件 → 收集其 _jump_targets →
#    [(目标页面类名, 条件, 描述, 来源控件类), ...]
```

**实现逻辑**：`@jump("LoginPage", cond, desc)` 以装饰器形式在控件类上累积 `_jump_targets` 列表（同名控件可叠加多行 `@jump` 表示多分支）。`_jump_entries()` 反查本页面全部跳转；`Page.ways_to(目标页, cond)` 遍历**所有 Page 类**的 `_jump_entries` 过滤出「能到目标页」的入口，返回 `[(描述, 条件, 来源页类, 来源控件类), ...]`。PO 层 `go_to_login()/go_home()` 据此自动选可用入口，无需硬编码跳转 id。

**要点**：目标以字符串类名引用（避免循环导入）；`cond` 支持登录态等分支判断；`ways_to` 是纯代码查询，不打开页面。

## 3 ElementResolver.locate_by —— 按平台优先级生成定位器（locator.py:222）

```python
def locate_by(self, element_cls) -> tuple[str, str]:
    platform_cls = self._platform_cls(element_cls)      # 取 web/android/ios 子类
    for attr in self._PRIORITY[self.platform]:          # 按平台优先级
        if not hasattr(platform_cls, attr): continue
        value = getattr(platform_cls, attr)
        if not isinstance(value, str) or not value: continue
        # web: css/id/xpath/tag/text→xpath/name
        # android: id→By.ID; xpath→By.XPATH; text→//*[@text='x' or @label='x'];
        #          class_name→By.CLASS_NAME; content_desc→//*[@content-desc='x']
        ...
```

**关键规则**：
- android 的 `id` 直接映射 `By.ID`（即 `resource-id`，形如 `tv.danmaku.bili:id/nick_name`），这是 Appium 原生支持的最稳定定位
- `text` 在 android 转双属性 XPath `[@text='x' or @label='x']`（覆盖 text 与 content-desc 两种现实）
- 关系定位控件（有 `relation`）走 `_resolve_relation()`，不在本办法内

## 4 ElementResolver._resolve_relation —— 关系定位（element.py:289）

```python
# CHILD_OF: parent_el.find_elements(By.XPATH, "./*") 取第 index 个子控件
# INSIDE:   parent_el.find_elements(By.XPATH, "./descendant::*")[index]
# ABOVE/BELOW/LEFT_OF/RIGHT_OF: 坐标法——
#   遍历全页元素，构造 rect，找出相对 parent 满足位置条件的所有元素，
#   按位置距离排序取第 index 个
```

**实现逻辑**：`parent` 引用同 Page 内另一个控件类 → `resolve()` 递归解析父控件 → 按关系类型取相对元素。坐标法用于「无特征控件相对参照物定位」的兜底。**失败抛 AssertionError**（便于测试定位），含候选数量诊断信息。

## 5 BaseOperates.find —— 软等待 + 并行滚动（base_operates.py:87）

```python
def find(self, page, name, timeout=None, wait_visible=True, scroll=False):
    element_cls = self._element_for(page, name)     # 不存在则抛 ValueError
    deadline = time.monotonic() + timeout
    # (a) 关系定位控件 → resolve 软等待重试（3.5s 间隔，直到 deadline）
    # (b) 属性定位 control →
    #     非 scroll：WebDriverWait(timeout).until(
    #                   visibility/presence_of_element_located((by, value)))
    #     scroll：起 daemon 线程，循环 find_element + swipe 下滑，
    #             直到找到或超时 → 取结果[0]
```

**返回**：WebElement；超时统一抛 `ElementNotFoundError`（含页面.控件名 + 等待时长）。
**关键决策**：默认等可见（`visibility`），纯存在性判断传 `wait_visible=False`；滚动模式由独立线程驱动真实滑动手势，主线程 `thread.join(timeout+1)` 兜底，避免阻塞主流程。

## 6 BaseOperates.click —— 快照对比 + 弹窗截获（base_operators.py:244）

```python
def click(self, page, name, popup_handler=None, expected=None, timeout=None, scroll=False):
    before = self._snapshot()                 # driver.current_url + driver.title（异常容错为 ""）
    element = self.find(...)
    try: element.click()
    except Exception: ActionChains.move_to_element().click().perform()   # 被遮挡→真实手势

    result = ClickResult()                      # url_changed/title_changed/popup_handled/...
    time.sleep(0.5)                             # 等弹窗/跳转稳定

    popup = self._detect_popup()               # web 端过滤：面积≥视口10% 且中心可见
    if popup:
        result.popup_text = popup.text[:200]
        if popup_handler is None: raise PopupError(...)   # 认为是缺陷
        if not popup_handler(popup, result.popup_text):   # 未处理/返回 False → 缺陷
            raise PopupError(...)
        result.popup_handled = True

    after = self._snapshot()
    result.url_changed / title_changed
    if expected == "url" and not url_changed: raise AssertionError("跳转失败")
    if expected == "title" and not title_changed: raise AssertionError(...)
    return result
```

**要点**：弹窗策略是「有处理函数且返回 True → 已处理；无处理函数/返回 False → 直接判为异常引发」，避免模态框吞掉后续步骤；`expected` 提供对点击跳转的内建断言，也可不传（仅做操作）。

## 7 DriverManager.create_driver —— 分平台建驱动（driver.py:136）

```python
def create_driver(self, name="main", platform="web", browser="edge", **kwargs):
    if name in self._drivers: raise ValueError(f"驱动已存在: {name}...")   # 重名保护
    driver = WebDriverFactory(platform, browser).create(**kwargs)
    if platform == "web":
        driver.set_page_load_timeout(self.page_load_timeout)   # web 才有 pageLoad 超时
    else:
        driver.implicitly_wait(10)                              # appium 用隐式等待
    self._drivers[name] = driver
    return driver
```

**关键决策**：appium driver **不能调用 `set_page_load_timeout`**（原生不支持 pageLoad 超时，`implicitly_wait` 才是移动端正确等待机制）；`name` 唯一性保证多驱动互不覆盖。WebDriverFactory（5.x）须用 `options`（`UiAutomator2Options`）构建 appium 会话，旧版传 dict 的方式会被弃。

## 8 PageObject.open —— 移动端冷启动（page_object.py:30）
```python
def open(self, url=None):
    package_name = getattr(self.page, "package_name", "")
    main_activity = getattr(self.page, "main_activity", "")
    if self.platform=="android" and package_name and main_activity:
        driver.terminate_app(package_name)  # 杀进程（失败忽略）
        driver.activate_app(package_name)     # 拉起回主 Activity → 冷启动
    elif self.platform in ("android","ios") and package_name:
        driver.activate_app(package_name)     # 无 main_activity 时仅前台化
    else:
        driver.get(url or self.page.url)      # web 端
    return self
```

**实现逻辑**：Android 端用「先杀再拉起」保证每次从主 Activity 首页开始（App 页面记忆被清除）；iOS 无 `start_activity` 语义故退化为 `activate_app`；`url` 缺省取 `self.page.url`。

## 9 PageObject.find / click / go_to（page_object.py:44）

```python
def find(self, name, **kwargs): return self.operates.find(self.page, name, **kwargs)
def click(self, name, **kwargs): return self.operates.click(self.page, name, **kwargs)
# go_to_login() ▸ 遍历 Page.ways_to(BilibiliLoginPage) 过滤来源 self.page →
#    试 click(locator.name, timeout=2) 成功 → 返回新页面 PO 对象
# is_logged_in() ▸ 20 次轮询 login_entry 与 avatar，能查到=已登录；否则读 cookies 兜底
```

## 10 TestCaseBase.run / checkPoint / step（base_test_case.py:19-46 / :103）

```python
def step(name):
    with allure.step(name):
        print(f"[STEP] {name}")

def checkPoint(name, actual=""):
    with allure.step(f"检查点：{name}"):
        if actual:
            print(f"[CHECKPOINT] {name} | 实际值: {actual}")
        else:
            print(f"[CHECKPOINT] {name}")

def run(self):
    try:
        self.setup()
        self.test_step()
    finally:
        try:
            self.teardown()
        finally:
            self._close_extra_drivers()
```

**实现逻辑要点**：
- **checkPoint 只登记不断言**（预期结果文本作为 docs 证据），断言由用例内 `assert` 完成；这是本框架的硬约定，Agent 与一致性检查都据此核对。
- **run 的 teardown 用 finally 嵌套保证无论成败必定执行**，并统一关闭用例内创建的附加驱动（释放 session）。

---

# 二、配套 Agent 实现解读

位置：`G:\AI\.config\opencode\agent\`，一套 **12 步流水线 + 8 个子 Agent**，把「文本用例 → 可运行测试脚本」全自动化。

## 2.1 编排者：uitest-pipeline

主 Agent（primary 模式，有 bash 权限），职责：

1. **解析输入**：收用户文本用例 → 从标题/主题生成 `CASE_ID`（kebab-case）
2. **初始化工作区**：建 `.pipeline\<CASE_ID>\` + `explore\` 子目录，原文写入 `00-case.txt`；已存在则断点续跑或询问覆盖
3. **顺序编排**：用 Task 工具按表依次调用 8 个子 Agent，**必须等待上一个完成**；每次传参：`CASE_ID`、`WORKSPACE`（绝对路径）、对应上游产物路径
4. **失败决策**：子 Agent 阻塞（如寻路 6 轮失败、调试 8 轮失败）→ 停止并向用户汇报卡点；一致性检查高严重度差异 → 回传给 debugger 一并修复
5. **收尾汇报**：最终用例路径与运行命令、工程改动汇总、中间产物目录、遗留风险

**两个硬规则**：① 8 个子 Agent 严格按序、禁止并行（存在产物依赖）；② 每步完成后校验产物存在且非空，缺失则让其重做。

## 2.2 子 Agent 全景表

| Agent | 流水线位置 | 核心职责 | 产物 | 权限要点 |
|---|---|---|---|---|
| `uitest-case-analyzer` | 1 拆解 | 文本拆成编号测试步骤，标注动作/预期/检查点/涉及页面 | `01-steps.md` | 只读，不改代码 |
| `uitest-page-mapper` | 2 映射 | 步骤映射到 PE 控件/PO 方法/跳转关系，输出缺口清单 | `02-page-map.md` | 只读 |
| `uitest-pathfinder` | 3-4 寻路 | 不写检查点、用 PO 真环境实际跑通，失败自愈（最多 6 轮） | `03-pathfinding-report.md`（可改 page/common/data） | 有 bash |
| `uitest-flow-refiner` | 5 业务流 | 把跑通链沉淀为可复用业务流接口，优先复用已有 | `04-flow-report.md`（可改 common） | 有 bash |
| `uitest-script-generator` | 6-7 生成 | 生成用例脚本框架 + 全部动作，检查点留 `# CHECKPOINT` 标记 | 脚本初稿 + `05-generator-report.md` | 只写 testcase/.pipeline |
| `uitest-checkpoint-writer` | 8 检查点 | `# CHECKPOINT` → `checkPoint` 登记 + `assert` 断言 | `06-checkpoint-report.md` | 只写 testcase/page/common |
| `uitest-consistency-checker` | 9 一致性 | 对照文本审核脚本覆盖/顺序/断言/多余操作 | `09-consistency-report.md` | 只读不改代码 |
| `uitest-script-debugger` | 10-12 调试 | 语法修复→调试→循环验证（最多 8 轮） | 最终脚本 + `12-debug-log.md` | 有 bash |

## 2.3 各子 Agent 关键设计点

### 拆解（uitest-case-analyzer）

- 一个步骤 = **一个独立用户动作或一个断言点**；保持文本动作顺序与上下文
- 允许补全隐含前置动作（如「打开首页」）但**不得臆造**文本没有的动作
- 检查点标记**宁少勿多**，只在文本明确写预期结果时标记
- 步骤数限制 3~30；单独列出前置条件 / 数据需求 / 后置恢复动作

### 映射（uitest-page-mapper）

- 必须基于**代码事实**：真实存在的 PE 控件名、PO 方法签名、`@jump`/`ways_to` 跳转关系；不确定的列为缺口，**禁止伪造**
- 产出「现有资产清单」（PE 页面与控件 / PO 方法 / 业务流接口）+「步骤映射表」+「缺口清单」（P 缺控件 / O 缺方法 / B 缺业务流 / R 跳转风险）
- 本步只记录不实现，缺口由 pathfinder / flow-refiner 补齐

### 寻路（uitest-pathfinder）—— 最有价值的一步

- **只趟通动作、不写断言**：写探路脚本 `explore\test_explore_<CASE_ID>.py`，按步骤调 PO 方法，每步 `print([EXPLORE][stepN] ...)` 便于定位
- **失败自愈循环（最多 6 轮）**：
  - 页面未跳转 → 重查 `ways_to` / 换入口 / 补改 jump 声明
  - 控件找不到 → 用 selenium-mcp 打开实际页面核实真实控件 → 修 PE 声明（含平台子类）
  - PO 方法缺失 → 补 PO 方法
  - 弹窗/倒计时 → 用 click 弹窗处理能力绕过
- 每轮失败 → 分析根因 → 修复 → 重试；每轮都记入报告
- 跑通后输出「最终稳定调用链」，供脚本生成与业务流沉淀使用

### 业务流沉淀（uitest-flow-refiner）

- **先查复用**：已有 flow（如 `BilibiliLoginFlow.login()` 分步方法）能整段/部分复用则优先
- 沉淀规范：继承 `BusinessFlow`、`_init_objects()` 实例化 PO 与 DataBase、分步方法 allure.step + 链式、完整流程一行串联、数据从 DataBase 取
- 同业务域追加/复用现有 flow；新域新建 flow 文件
- 冒烟验证：写临时探路脚本调用新接口跑通（无检查点）

### 脚本生成（uitest-script-generator）

- 严格对照现有样例（`test_bilibili_login_scenario.py`）写框架：类结构 + pytest 入口 + `TestCaseBase` 继承
- 框架：`_init_objects` / `setup` / `test_step` / `teardown` 四段式
- **本步不写最终检查点断言**，在检查点位置留 `# CHECKPOINT:<步骤N> <预期结果>` 标记

### 检查点补全（uitest-checkpoint-writer）—— 重点约定

每个检查点输出**两行**：

```python
checkPoint("「预期结果文本」", f"实际: {实际值}")   # 仅登记，不断言
assert <条件>, "中文失败原因（提示根因）"            # 原生 assert 负责校验
```

硬性规则：
- **禁止在 checkPoint 内实现断言**（如 `checkPoint(name, 布尔条件)`）；checkPoint 仅登记预期结果文本
- 只补「文本中明确写了预期结果」的检查点，不额外加断言（宁缺勿多）
- 预期结果文本原样取自 `01-steps.md`；失败信息要能指导排查（如「点击后未跳转到预期页面，可能是…」）
- 校验方式参考 `common/base_operates.py` 能力：页面状态类 / 跳转类（`click(..., expected=)`）/ 文本元素存在类

### 一致性检查（uitest-consistency-checker）

对照维度：**步骤覆盖 / 顺序一致 / 动作一致 / 检查点覆盖（登记 + 断言缺一即不完整）/ 无多余操作 / 数据一致**。

输出核对表 + 差异清单（按高/中/低严重度排序）；高严重度差异（缺步骤/顺序颠倒/检查点缺失）必须明确列出。

### 调试（uitest-script-debugger）

三步走：
1. **步骤10 语法修复**：`py_compile` + 读代码修语法/导入/缩进（含 09 报告代码层差异）
2. **步骤11 脚本调试**：运行单用例（`-m web`），PASS 进入下一步
3. **步骤12 循环验证（最多 8 轮）**：读失败堆栈 + allure 报告（含失败截图）定位失败层：

| 根因分类 | 处置 |
|---|---|
| 脚本逻辑错误 | 修 testcase |
| 业务流接口缺陷 | 修 common |
| 控件定位失效/跳转错误 | selenium-mcp 核实真实控件 → 修 PE/PO |
| 等待不足 | 调整软等待（禁止乱加 time.sleep） |
| 环境问题（网络/驱动/验证码/账号数据） | 确认后记录，作为阻塞项上报，不改框架 |

禁止：改 conftest.py / pytest.ini / UITest.md 等框架文件；为通过用例而删除检查点断言；硬编码账号密码。

---

# 三、实战复盘（Android 真机）

以 `text_case.md`（打开 App → 点击我的 → 点击头像 → 校验昵称「励志成为雏生大王_406」）为例，验证整套体系：

### 遇到的问题与根因

| # | 现象 | 根因 | 修复 |
|---|---|---|---|
| 1 | `page_load_timeout` 报错 | appium 5.x 用 options 参数 + 不支持 pageLoad | driver.py 分平台设置超时 |
| 2 | `start_activity` AttributeError | appium client 5.3.1 移除该方法 | `open()` 改 terminate_app + activate_app 冷启动 |
| 3 | wait_loaded 找不到 nav_top_bar | App 默认停「直播」Tab，nav_top_bar 只在首页 | 加载标志改底部「我的」导航 |
| 4 | 定位全错但无显式报错 | 用例入口未传 platform，默认 "web" | conftest 加 `platform_config` fixture，入口注入 |
| 5 | ANDROID_HOME 缺失 | appium server 启动时无环境变量 | 重启 server 携带环境变量 |
| 6 | 设备 instrumentation 崩溃 | MCP 会话与 pytest 会话同时占设备 | 只保留一个会话 |

### 最终结果

```
testcase/test_bilibili_my_nickname.py::test_bilibili_my_nickname PASSED
1 passed in 51.81s
```

---

# 四、核心小结

## 工程侧

1. **六层架构**：PE（元素+跳转声明）→ PO（页面对象）→ BaseOperates（操作重构）→ Driver（多端控制）→ BusinessFlow（业务流）→ TestCaseBase（用例结构）
2. **跳转声明反查**：`@jump` + `ways_to` 让页面跳转「查码不查页面」
3. **操作重构**：find 软等待/并行滚动、click 快照+弹窗截获、swipe 手势化
4. **checkPoint 只登记、assert 负责断言**：检查点记录证据，判定交给代码
5. **易错点**：platform 必须注入用例；appium server 环境变量要齐；多会话不得独占设备；App 页面记忆需冷启动清除

## Agent 侧

1. **12 步流水线 + 8 个子 Agent**，严格顺序、禁止并行、产物校验
2. **寻路是灵魂**：真环境实际跑通 + 失败自愈（最多 6 轮），产出稳定调用链
3. **检查点约定**：`checkPoint` 登记 + `assert` 断言两行式，宁缺勿多
4. **调试兜底**：最多 8 轮循环，按失败层分类处置，环境问题不硬扛

---

*附：本文档与 `docs\UITest-框架实现详解.md` 互为补充——后者偏工程框架原理，本文档覆盖工程 + Agent 全貌。*
