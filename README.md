# UITest 框架说明

基于 pytest + selenium + allure 的测试框架
能够实现 Web 系统的自动化测试

GitHub：[406w/UITest](https://github.com/406w/UITest)。Docker Jenkins 配置与部署方式见 [ci/JENKINS.md](ci/JENKINS.md)。仓库包含 demo/erp 演示服务，可独立执行 `python main.py --isolated`；Windows 默认 Edge，容器流水线使用远程 Chrome。

**工程已实现。** 运行命令、真实 ERP 场景与扩展方式见 [使用与验证](使用与验证.md)，实测结果见 [验证记录](验证记录.md)。下方伪代码保留为设计参考；可运行代码以各 Python 文件为准。

## 工程结构

文本用例转脚本的 OpenCode agent 集合见 [.opencode/erp-uitest/README.md](.opencode/erp-uitest/README.md)，包含总编排、八个专职角色、共享约定与登录/订单文本示例。

```
ERP-UITest/
├── readme.md                  # 本框架说明（规则文档）
├── pytest.ini                 # pytest 配置
├── conftest.py                # driver fixture + 失败自动截图
├── requirements.txt           # 依赖清单
├── requirements.lock.txt      # 已验证的精确依赖版本
├── main.py                    # 执行入口，可启动隔离 ERP 并生成报告
├── page/                      # 页面层
│   ├── page_elements/         # PE 页面元素层（每个页面对应一个文件，声明页面控件）
│   │   ├── home_page.py       # Page 页面基类，存在一些业务需要的元素对象没有明确的特征属性，此类控件只在声明后写入描述，后续再PO层做具体实现
│   │   ├── login_page.py
│   │   └── order_page.py      # 订单列表、编辑与详情声明
│   └── page_objects/          # PO 页面对象层（每个页面文件对应一个操作文件，输出页面元素对象，关联元素对象与其他页面的跳转关系）
│   │   ├── locator.py         # jump 跳转装饰器， ways_to 反查（查找元素对象与页面的跳转关系）
│   │   ├── home_po.py         # 链式调用，输出元素对象，关联元素对象与其他页面的跳转关系（对PE层仅声明描述的控件，在此处通过相对关系输出元素对象）
│   │   ├── login_po.py
│   │   └── order_po.py        # 采购/销售订单操作及测试草稿恢复
├── common/                    # 公共层
│   ├── config.py              # 运行配置及用例上下文
│   ├── elements.py            # 嵌套元素类的解析与条件校验
│   ├── base_operates.py       # BaseOperates 类，重构操作（find 软等待/并行滚动、click 快照/弹窗截获、swipe 手势重构）
│   ├── base_checks.py         # BaseChecks 类，重构校验（依据业务的检查点校验需求，封装校验逻辑）
│   ├── driver.py              # Driver工厂，负责统一创建驱动、重置驱动、处理异常
│   ├── test_case.py           # TestCase 类，按 init/setup/process/teardown 组织面向对象用例
│   ├── action_write.py        # AW 类，业务操作（串联 PO 操作，复用业务场景）
│   ├── report.py              # step/checkpoint 标题步骤、阶段收尾与 Allure 适配
│   └── report_config.py       # pytest/IDE 默认结果目录、HTML 生成与报告索引
├── data/                      # 测试基础数据（sqlite）
│   ├── db.db                  # 运行时生成在独立临时目录，不提交共享数据库
│   ├── data.yaml              # yaml 数据文件
│   └── database.py            # 测试数据处理类（读取、写入、初始化）
├── testcase/                  # 测试用例层
│   ├── test_login.py          # 登录成功、错误密码
│   ├── test_logout.py         # 退出及刷新后会话校验
│   └── test_orders.py         # 销售/采购草稿及恢复
├── framework_checks/          # 框架边界与失败路径验证
└── report/                    # 测试报告
    ├── allure-results/        #    原始结果（pytest --alluredir 生成）
    └── allure-report/         #    HTML 报告（allure generate 生成）
```

## 技术设计与伪代码（保留的设计参考）

以下保留已确认的接口约定和流程设计，采用接近 Python 的伪代码，不能直接执行；完整实现及实际定位已写入工程源码，运行方式见文档顶部链接。

登录场景仅用于说明层间调用，实际页面地址、元素属性、登录成功标志和测试数据字段需依据 ERP 系统确认。文中的 `wait_until`、`attach_safely` 等函数代表待实现的辅助逻辑。

### 1. 分层职责与调用约定

```text
pytest 用例 → AW 业务操作 → PO 页面对象 → BaseOperates → Selenium Driver
                              ↓
                         PE 元素声明
pytest 用例 → BaseChecks → PO/元素对象
fixture → DriverFactory + Database + 用例生命周期
pytest 报告 hook → 失败证据 → Allure
```

| 模块 | 主要职责 | 输出或约束 |
| --- | --- | --- |
| PE | 声明元素标识、描述和定位信息 | 不访问浏览器，不执行操作 |
| PO | 解析元素、处理页面关系、封装页面操作 | 同页操作返回自身，成功跳转返回目标 PO |
| BaseOperates | 等待、定位、点击、输入、滚动和手势 | 每次操作重新定位，避免长期缓存 WebElement |
| BaseChecks | 封装业务检查点 | 失败抛出带预期值与实际值的断言异常 |
| AW | 串联多个 PO 完成业务流程 | 不直接编写选择器，不捕获并忽略失败 |
| TestCase / fixture | 组织初始化、前置、步骤、清理 | pytest 负责调度，fixture 负责资源释放 |
| Database | 初始化、读取和保存测试基础数据 | 参数化 SQL、事务提交、失败回滚 |

`home_page.py` 直接声明首页元素，不要求继承公共元素基类；`home_po.py` 中放置公共 PO 基类及首页 PO。此处暂不增加文件。

### 2. PE：元素声明

```python
# page/page_elements/home_page.py
class HomePage:
    class login:
        """登录按钮"""
        id = "43656"
        type = "button"
        text = "登录"

    class ready:
        """首页就绪标志"""
        id = "home-content"                  # 示例属性，按实际 DOM 确认

    class user_menu:
        """当前用户菜单"""
        id = "current-user"

    class order_entry:
        """订单区域内的进入按钮"""           # 无稳定属性，由 PO 实现相对定位

# page/page_elements/login_page.py
class LoginPage:
    class username:
        """账号输入框"""
        name = "username"
        tag = "input"

    class password:
        """密码输入框"""
        name = "password"
        type = "password"

    class submit:
        """登录按钮"""
        type = "submit"
        text = "登录"

    class error:
        """登录错误提示"""
        css = ".login-error"
```

页面类作为元素命名空间，内部类就是元素声明，直接使用 `HomePage.login`，无需实例化或填写重复的 key。内部类的名称是页面内元素标识，文档字符串是描述；页面标识由 PO 的 `page_key` 维护。PE 只保存静态声明，运行时状态放在 PO 或 ElementHandle 中。

| 声明字段 | 含义与解析规则 |
| --- | --- |
| `id`、`name`、`type` | 匹配同名 HTML 属性；`type="button"` 表示 DOM 的 type 属性 |
| `tag` | HTML 标签名；若需要匹配 `<button>`，使用 `tag="button"` |
| `text` | 元素可见文本去除首尾空白后精确匹配 |
| `css`、`xpath` | 可选的显式定位表达式，两者不同时声明 |
| `attrs` | 扩展 HTML 属性，如 `attrs = {"data-testid": "login", "aria-label": "登录"}` |
| `meta` | 可选扩展元数据，由相应功能读取，不参与定位 |

所有已声明的定位条件按“同时满足”处理，不将 `id`、`type`、`text` 当成相互替代的备用定位。优先用 `css/xpath`、`id`、`name`、`tag` 等缩小候选范围，再检查其余属性和文本；不满足时继续等待，多个匹配时报歧义异常。无定位字段时交由 PO 的相对定位实现，不用描述文本自动查找。

新增 HTML 属性通常只需扩展 `attrs`；新增框架语义字段需在公共解析器注册处理器。未注册字段应明确报错，避免拼写错误被静默忽略。`attrs` 与快捷字段重复声明同一属性时，应校验其值一致。

```python
# 以下辅助逻辑放在公共操作层，PE 本身保持纯声明。
def element_key(declaration):
    return declaration.__name__              # HomePage.login → "login"

def element_description(declaration):
    return clean_docstring(declaration) or declaration.__qualname__

def parse_declaration(declaration):
    fields = read_public_class_attributes(declaration)
    validate_registered_fields_and_conflicts(fields)
    return normalize_conditions(fields)      # 保留所有条件，不修改声明类

def resolve_declared_element(driver, declaration):
    conditions = parse_declaration(declaration)
    if not conditions.has_locator_conditions:
        raise MissingResolver(declaration.__qualname__)
    candidates = find_candidates(driver, conditions)  # 动态属性值必须正确转义
    matches = filter_by_all_conditions(candidates, conditions)
    if len(matches) == 0:
        raise NoSuchElement(element_description(declaration))
    if len(matches) > 1:
        raise AmbiguousElement(declaration.__qualname__, len(matches))
    return matches[0]
```

### 3. Driver：驱动创建、重置与异常处理

```python
# common/driver.py
class DriverFactory:
    create(config):
        driver = None
        try:
            options = build_browser_options(config.browser, config.headless)
            driver = create_webdriver(options)
            driver.implicitly_wait(0)          # 等待统一交给显式轮询
            driver.set_page_load_timeout(config.page_load_timeout)
            driver.set_window_size(config.width, config.height)
            return driver
        except Exception:
            quit_safely(driver)               # 创建到一半失败也释放进程
            raise

    reset(context):
        quit_safely(context.driver)
        context.driver = None
        context.driver = create(context.config)
        # PO/操作对象都通过 context 获取当前驱动；禁止缓存旧 WebElement。
        # 重置仅作为显式恢复动作，不自动重放可能已经提交的业务操作。

    close(context):
        quit_safely(context.driver)
        context.driver = None
```

默认每条用例独立创建驱动，避免登录态和页面状态互相污染。驱动失联时让当前用例失败并收集可用信息，由下一条用例创建新会话。

### 4. BaseOperates：统一元素操作

“软等待”约定为超时范围内轮询查找，不代表忽略必需元素缺失。“并行滚动”在此设计为查找与分段滚动交替执行；同一 WebDriver 会话不使用多线程同时发送命令。滚动容器由 PO 指定，默认使用页面视口。

```python
# common/base_operates.py
class ElementHandle:
    init(ops, declaration, resolver):
        save(ops, declaration, resolver)       # 保存元素声明类，不实例化 PE
        self.description = element_description(declaration)

    fill(value, sensitive=False):
        element = ops.find(resolver, condition="editable")
        element.clear()
        element.send_keys(value)
        log_input(self.description, "***" if sensitive else value)
        return self

    click(alert_policy="fail"):
        ops.click(resolver, self.description, alert_policy)
        return self

    text():
        return ops.find(resolver, condition="visible").text

class BaseOperates:
    init(context):
        self.context = context

    find(resolver, condition="visible", required=True, scroll_container=None):
        deadline = monotonic_now() + context.config.element_timeout
        while monotonic_now() < deadline:
            try:
                element = resolver(context.driver)
                if matches(element, condition):
                    return element
            except (NoSuchElement, StaleElement):
                pass                          # 只重试可恢复的定位异常
            if scroll_container is not None:
                scroll_one_bounded_step(scroll_container)
                # 到边界后停止滚动，查找仍受总超时限制
            sleep(context.config.poll_interval)
        if required:
            raise ElementTimeout(description, timeout, current_url)
        return None

    click(resolver, description, alert_policy):
        element = find(resolver, condition="clickable")
        attach_safely("点击前：" + description, screenshot_if_allowed())
        element.click()                       # 已发出的点击不盲目重试
        handle_expected_alert(alert_policy, bounded_alert_wait)
        # accept/dismiss 只在调用方明确指定时执行；默认意外弹窗使操作失败。
        # DOM 模态框由 PO 定位与处理，不当作浏览器原生 alert。
        attach_safely("点击后：" + description, screenshot_if_allowed())

    swipe(container, direction, distance):
        validate_direction_and_distance()
        origin = resolve_container_bounds(container)
        perform_pointer_or_wheel_action(origin, direction, distance)
        wait_until_scroll_settles_with_timeout()
```

截图附件失败只记录诊断信息，不能覆盖操作本身的异常。涉及密码、令牌或敏感页面时，应按配置关闭截图或对已知区域脱敏；密码输入与业务步骤日志不记录明文。

### 5. PO：元素解析与链式操作

```python
# page/page_objects/home_po.py
class BasePO:
    init(context):
        self.context = context
        self.ops = BaseOperates(context)

    element(declaration):
        resolver = lambda driver: self.resolve(driver, declaration)
        return ElementHandle(self.ops, declaration, resolver)

    resolve(driver, declaration):
        return resolve_declared_element(driver, declaration)

    wait_ready():
        ABSTRACT                              # 每个页面定义自己的就绪条件

class HomePO(BasePO):
    page_key = "home"

    wait_ready():
        ops.find(lambda d: resolve(d, HomePage.ready))
        return self

    resolve(driver, declaration):
        if declaration is HomePage.order_entry:
            region = find_unique_business_region(driver, "订单")
            return find_unique_relative_button(region, "进入")
            # 相对定位依赖真实 DOM；匹配多个时显式报错，不默认取第一个。
        return super().resolve(driver, declaration)

    current_user():
        return element(HomePage.user_menu).text()

# page/page_objects/login_po.py
class LoginPO(BasePO):
    page_key = "login"

    open():
        context.driver.get(context.config.base_url + CONFIRMED_LOGIN_PATH)
        return wait_ready()

    wait_ready():
        ops.find(lambda d: resolve(d, LoginPage.username))
        return self

    enter_username(value):
        element(LoginPage.username).fill(value)
        return self

    enter_password(value):
        element(LoginPage.password).fill(value, sensitive=True)
        return self

    @jump(source="login", element_key=element_key(LoginPage.submit), target="home")
    submit_success():
        element(LoginPage.submit).click()
        # 装饰器等待首页就绪，返回 HomePO。

    submit_rejected():
        element(LoginPage.submit).click()
        ops.find(lambda d: resolve(d, LoginPage.error))
        return self                           # 失败登录留在当前页
```

### 6. jump 与 ways_to：跳转声明和反查

跳转登记使用页面字符串标识，避免 PO 互相导入。登记是元数据操作，不应触发浏览器访问。`ways_to` 返回直接入口列表，不自动规划路径或执行点击。

```python
# page/page_objects/locator.py
PAGE_TYPES = {}                               # page_key → PO 类型
ROUTES = {}                                   # (source, action) → 路由元数据

def jump(source, element_key, target):
    def decorate(action):
        register_unique(ROUTES, (source, action.name),
                        {source, element_key, target, action.name})
        @preserve_metadata(action)
        def wrapped(self, *args, **kwargs):
            assert self.page_key == source
            target_type = PAGE_TYPES[target]   # 执行动作前验证配置
            action(self, *args, **kwargs)
            target_po = target_type(self.context)
            target_po.wait_ready()            # 跳转未完成必须失败
            return target_po
        return wrapped
    return decorate

def initialize_page_registry():
    import_all_declared_po_modules()           # 加载全部装饰器，防止反查遗漏
    PAGE_TYPES.update({"login": LoginPO, "home": HomePO})
    validate_route_sources_targets_and_element_keys()
    # 元素 key 对应源页面 PE 的内部类名，如 LoginPage.submit → "submit"。

def ways_to(target, source=None):
    return [route for route in ROUTES.values()
            if route.target == target
            and (source is None or route.source == source)]

# ways_to("home") 示例结果：
# [{source: "login", element_key: "submit", target: "home",
#   action: "submit_success"}]
```

一个按钮的不同业务结果可以由不同方法表达，如成功登录与失败登录。装饰器只描述方法承诺的成功路径，不表示点击后必然跳转。

### 7. BaseChecks 与 AW：检查点和业务复用

```python
# common/base_checks.py
class BaseChecks:
    equal(actual, expected, description):
        if not current_report().has_title():
            checkpoint(description)
        assert actual == expected, format_safe_diff(expected, actual)

    eventually(read_actual, expected, description, timeout):
        if not current_report().has_title():
            checkpoint(description)           # 等待过程也属于该检查点
        # 仅对无副作用的读取轮询；超时报告最后一次实际值。
        actual = poll_read_until_equal(read_actual, expected, timeout)
        equal(actual, expected, description)

# common/action_write.py
class AW:
    init(context):
        self.context = context

    open_webpage():
        return LoginPO(self.context).open()    # 打开本示例的 ERP 登录页

    login_as(account):
        if not current_report().has_title():
            step("使用测试账号登录")
        return (LoginPO(context).open()
                .enter_username(account.username)
                .enter_password(account.password)
                .submit_success())
```

### 7.1 报告封装：step 与 checkpoint

用例采用“先声明标题，再执行操作”的写法，无需为每个步骤编写 with：

```python
from common.report import step, checkpoint

step("步骤1：打开网页")
login = self.aw.open_webpage()

checkpoint("检查点1：登录页已打开")
self.checks.equal(self.context.driver.current_url, expected_url, "核对页面地址")
```

`self.aw` 是当前用例的 AW 实例，表达示意中 `AW.open_webpage()` 的业务调用。`step` 与 `checkpoint` 都是框架自定义方法，底层管理 Allure 步骤上下文，输出标题、耗时、状态、异常与附件。Allure 的原生上下文能力见 [Allure Pytest 步骤文档](https://allurereport.org/docs/pytest-reference/#test-steps)。

约定如下：

- `step(title)` 开始操作步骤，`checkpoint(title)` 开始检查点步骤，按原样展示传入的标题。二者在 Allure 中都表现为步骤，不假设 Allure 有原生 checkpoint 类型。
- 新标题开始前关闭上一标题步骤；期间的全部操作、校验和附件归属当前步骤，不能只记录标题后立即关闭。
- 每个 init/setup/process/teardown 阶段结束时自动关闭最后一个步骤；阶段失败时将异常信息传给当前步骤，再向 pytest 抛出原异常。
- checkpoint 只声明检查范围，后面的 BaseChecks 或 assert 决定结果。断言失败后默认停止执行；被业务代码捕获且未重新抛出的异常不会自动标记失败。
- 用例、AW 和校验层均采用 step/checkpoint 标题记录，不再提供 report_block。标题范围由调用方划分；AW/校验方法在已有标题时沿用当前步骤，无标题时可补充默认标题，避免关闭调用方的步骤或产生重复记录。
- 普通方法返回不结束标题范围；同一标题可包含多个方法。需要新步骤时显式调用 step/checkpoint，当前设计不自动生成业务嵌套步骤。
- 没有活动阶段时调用 step/checkpoint 应报使用错误。每个阶段独立创建报告状态，通过 ContextVar 隔离；当前设计不支持同一用例多个异步任务并发写入步骤。

```python
# common/report.py（伪代码，Allure 调用集中在此模块）
import allure
import sys
from contextvars import ContextVar

active_report = ContextVar("active_report", default=None)

class StepReporter:
    def __init__(self):
        self.current = None

    def has_title(self):
        return self.current is not None

    def begin(self, kind, title):
        validate_nonempty_title(title)
        self.finish()                         # 前一步正常完成
        scope = allure.step(title)
        scope.__enter__()                     # 保持打开，覆盖后续操作
        self.current = scope
        # kind 用于框架日志分类，标题由调用者提供。

    def finish(self, exc_info=(None, None, None)):
        scope = self.current
        self.current = None                   # 防止重复关闭
        if scope is not None:
            scope.__exit__(*exc_info)

def current_report():
    reporter = active_report.get()
    if reporter is None:
        raise ReportUsageError("请在用例生命周期内声明步骤")
    return reporter

def step(title):
    current_report().begin("step", title)

def checkpoint(title):
    current_report().begin("checkpoint", title)

def run_phase(title, action, context):
    reporter = StepReporter()
    token = active_report.set(reporter)
    phase_scope = None
    try:
        scope = allure.step(title)            # 框架管理阶段容器
        scope.__enter__()
        phase_scope = scope
        try:
            result = action()
            reporter.finish()                 # 正常返回时关闭最后一个标题
        except BaseException:
            original_error = sys.exc_info()
            # 先截图后关闭，使证据归入当前失败的标题步骤。
            capture_failure_safely(context, phase=title)
            finish_preserving_original_error(reporter, original_error)
            closing_scope, phase_scope = phase_scope, None
            close_scope_preserving_original_error(closing_scope, original_error)
            raise                             # 不吞掉异常，不继续后续步骤
        else:
            closing_scope, phase_scope = phase_scope, None
            closing_scope.__exit__(None, None, None)
            return result
    finally:
        active_report.reset(token)

def finish_preserving_original_error(reporter, original_error):
    try:
        reporter.finish(original_error)
    except BaseException as report_error:
        log_report_error_safely(report_error)  # 保留业务原异常

def close_scope_preserving_original_error(scope, original_error):
    try:
        scope.__exit__(*original_error)
    except BaseException as report_error:
        log_report_error_safely(report_error)
```

`capture_failure_safely` 同样放在公共报告模块，供 run_phase 和 pytest hook 共用，避免公共层反向依赖 conftest。普通断言与其他异常的报告状态由 Allure 根据传入异常映射。阶段内异常先关闭标题步骤，再关闭阶段步骤，最后交给 pytest 记录。

所有失败证据入口共用去重机制：按“用例 nodeid + pytest 阶段 setup/call/teardown”记录是否成功采集，成功后其他入口跳过；采集失败允许后续入口重试。init/setup 均属于 pytest setup 阶段。未进入 run_phase 的资源准备失败仍由 hook 兜底。

预期报告结构（第 10 节登录示例的 process 阶段）：

```text
process：测试步骤
├── 步骤1：打开网页                     状态 / 耗时
├── 步骤2：输入账号并登录               状态 / 耗时
└── 检查点1：首页展示当前登录用户       状态 / 耗时 / 失败截图
```

后续实现时验证：连续标题生成同级步骤、最后一步正常收尾、断言失败状态和截图归属正确、失败后不执行下一标题、teardown 仍执行，以及不同用例之间没有残留步骤。此处仅增加设计伪代码，不创建 report.py 或运行 Allure。

### 8. Database：YAML 初始化与 SQLite 数据访问

SQLite 保存测试输入和预期值，不直接替代 ERP 后端数据，也不直接修改 ERP 生产库。`data.yaml` 中保存非敏感基础数据及密码环境变量名称，运行时解析密码。每次运行复制独立 SQLite 数据库；将来启用多进程时，每个 worker 使用独立副本。

```yaml
# data/data.yaml 示意；账号和预期展示名以测试环境为准
accounts:
  - key: normal_user
    username: test_user
    password_env: ERP_TEST_PASSWORD
    expected_display_name: 测试用户
```

```python
# data/database.py
class Database:
    open(path):
        self.connection = sqlite_connect(path)
        return self

    initialize(yaml_path):
        data = yaml_safe_load(yaml_path)
        validate_schema_and_unique_keys(data)
        with transaction(self.connection):
            create_accounts_table_if_missing()  # key 是唯一键
            for row in data.accounts:
                execute_parameterized_upsert(row)
                # 保存 password_env 名称，不保存解析出的密码。

    account(key):
        row = query_one("SELECT * FROM accounts WHERE key = ?", [key])
        if row is None:
            raise MissingTestData(key)
        return Account(row, password=required_env(row.password_env))

    save_account(row):
        validate_account(row)
        with transaction(self.connection):
            execute_parameterized_upsert(row)
            # 正常退出提交，异常退出回滚。

    close():
        close_connection_if_open()
```

### 9. TestCase：面向对象用例生命周期与 pytest 适配

每个具体用例脚本定义一个继承 `TestCase` 的类，以实例属性共享各阶段的数据，只需实现以下四个方法：

| 方法 | 职责 |
| --- | --- |
| `init(self)` | 初始化用例数据、页面对象、预期结果及恢复状态 |
| `setup(self)` | 执行预置步骤，使业务环境满足测试前提 |
| `process(self)` | 执行测试步骤及检查点 |
| `teardown(self)` | 恢复本用例修改的部分业务环境，如删除临时数据或恢复设置 |

调用顺序为 `init → setup → process → teardown`。用例不定义自定义构造函数，pytest 负责创建实例。公共属性的类型和赋值在 TestCase 中显式定义，fixture 在 init 前调用 bind_resources 完成绑定；四个生命周期方法都只接收 self。浏览器与数据库连接由 fixture 管理，业务环境恢复由用例自身负责。

pytest 收集具体用例类继承的唯一入口 `test_process`，由它调用 `self.process()`。具体用例只实现四个生命周期方法，无需模块级测试函数或 indirect 参数化适配。fixture 在 yield 前执行 init/setup，在调用 init 前登记 teardown，保证 init/setup/process 失败时仍尝试恢复。

```python
# common/test_case.py
class TestCase:
    __test__ = False                           # 基类本身不作为测试收集
    context: Context
    database: Database
    aw: AW
    checks: BaseChecks

    def bind_resources(self, context: Context, database: Database):
        self.context = context
        self.database = database
        self.aw = AW(context)
        self.checks = BaseChecks(context)

    def init(self):
        pass                                  # 子类初始化自身属性

    def setup(self):
        pass                                  # 子类执行预置步骤

    def process(self):
        raise NotImplementedError("用例必须实现 process(self)")

    def teardown(self):
        pass                                  # 子类恢复部分业务环境

    def test_process(self):
        run_phase("process：测试步骤", self.process, self.context)
        # 框架统一入口，阶段退出时关闭最后一个标题步骤。

# conftest.py
@fixture(scope="session")
def runtime_config():
    config = load_and_validate_cli_env_config()
    initialize_page_registry()
    return config

@fixture(scope="session")
def database(runtime_config, temporary_directory):
    db = Database().open(unique_run_database_path(temporary_directory))
    try:
        db.initialize("data/data.yaml")
        yield db
    finally:
        db.close()

@fixture(scope="function")
def context(request, runtime_config):
    ctx = Context(config=runtime_config, driver=None)
    request.node.ui_context = ctx
    try:
        ctx.driver = DriverFactory.create(runtime_config)
        yield ctx
    finally:
        DriverFactory.close(ctx)

@fixture(autouse=True, scope="function")
def case_lifecycle(request):
    case = request.instance
    if not isinstance(case, TestCase):
        yield
        return
    ctx = request.getfixturevalue("context")
    db = request.getfixturevalue("database")
    case.bind_resources(context=ctx, database=db)

    def restore_case_environment():
        try:
            run_phase("teardown：环境恢复", case.teardown, ctx)
        except Exception:
            capture_failure_safely(ctx, phase="business_teardown")
            raise                             # 独立记录为 pytest teardown 错误

    request.addfinalizer(restore_case_environment)
    # 即使在 yield 前失败，已登记的 finalizer 仍会执行。
    try:
        run_phase("init：用例初始化", case.init, ctx)
        run_phase("setup：预置步骤", case.setup, ctx)
    except BaseException:
        # yield 前失败时先截图，随后由 finalizer 恢复环境。
        capture_failure_safely(ctx, phase="init_or_setup")
        raise
    yield                                     # pytest 调用 case.test_process()

@hookwrapper
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    if report.failed:
        ctx = getattr(item, "ui_context", None)
        capture_failure_safely(ctx, phase=report.when)
        # setup/call 阶段驱动通常仍可用；teardown 报告产生时可能已关闭。
        # 无驱动时仅附加可用日志，不尝试重启，不覆盖原始异常。

# common/report.py（公共证据采集方法，供阶段调度及 hook 共用）
def capture_failure_safely(ctx, phase):
    try:
        if ctx and session_is_available(ctx.driver):
            attach_screenshot_if_allowed(unique_name(phase))
            attach_redacted_url_and_available_logs()
        else:
            attach_available_diagnostics(phase)
    except Exception as evidence_error:
        log_evidence_collection_error(evidence_error)
```

业务恢复先于驱动关闭；数据库与驱动各自通过 fixture 的 `finally` 释放。init/setup 只完成一部分也会进入 `teardown`，子类应通过属性存在检查或恢复记录保证恢复可重复、可部分执行。若前置或测试步骤已失败，恢复又失败，pytest 分别报告原始失败和 teardown 错误，不能用恢复异常替换原始失败。框架依赖准备失败、尚未进入 init 时，仅释放已创建的框架资源。

### 10. 用例示例与执行闭环

```python
# testcase/test_login.py（仅为未来文件示例）
from common.report import step, checkpoint

class TestLogin(TestCase):
    __test__ = True                            # 收集具体用例及继承的测试入口

    def init(self):
        self.account = self.database.account("normal_user")
        self.login = LoginPO(self.context)
        self.home = None

    def setup(self):
        pass                                  # 示例无需额外预置

    def process(self):
        step("步骤1：打开网页")
        self.login = self.aw.open_webpage()

        step("步骤2：输入账号并登录")
        self.home = (self.login
                     .enter_username(self.account.username)
                     .enter_password(self.account.password)
                     .submit_success())

        checkpoint("检查点1：首页展示当前登录用户")
        self.checks.eventually(
            read_actual=self.home.current_user,
            expected=self.account.expected_display_name,
            description="首页展示当前登录用户",
            timeout=self.context.config.element_timeout,
        )

    def teardown(self):
        # 本示例只清理本浏览器的 cookie；不代表服务端退出登录。
        # 真实 ERP 如需撤销服务端会话或恢复业务数据，调用对应恢复操作。
        step("恢复步骤：清理浏览器 cookie")
        self.context.driver.delete_all_cookies()
```

```text
读取配置并登记页面关系
  → 为用例创建浏览器，初始化本次运行的测试数据
  → 向 pytest 创建的实例注入依赖 → 登记环境恢复 → init → setup
  → pytest 执行继承的 test_process → TestLogin.process
  → LoginPO → 元素操作 → jump → HomePO.wait_ready
  → BaseChecks 校验当前用户
  → 生成 call 阶段报告，失败时截图
  → 业务 teardown（失败时在驱动关闭前截图）
  → 关闭驱动 → 生成 teardown 阶段报告
  → 全部用例结束后关闭数据库 → 汇总 Allure 原始结果
```

### 11. 配置草案与后续实现验收

```ini
# pytest.ini 草案，后续落地时创建
[pytest]
testpaths = testcase
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = -ra
```

依赖职责：`pytest` 负责用例调度，`selenium` 负责浏览器操作，`allure-pytest` 负责报告附件，`PyYAML` 负责数据读取，`sqlite3` 使用 Python 标准库。Allure 报告生成命令需要独立安装对应命令行工具；具体版本在实现时验证并固定。

运行配置至少包括 `base_url`、`browser`、`headless`、窗口尺寸、页面加载超时、元素等待超时、轮询间隔、截图开关和敏感区域策略。地址与非敏感参数可来自配置或命令行，凭据来自环境变量。

```text
# 工程实现后才可执行；当前仅说明预期使用方式
pytest --alluredir=report/allure-results/<run_id>
allure generate report/allure-results/<run_id> -o report/allure-report/<run_id>
```

后续实现时优先验证以下行为：

- 正常登录返回首页 PO，错误凭据场景保留在登录 PO 并检查错误信息。
- 必需元素超时使测试失败，可选元素超时返回 None，查找与滚动有明确边界。
- 无稳定属性的元素通过 PO 相对定位解析，出现多个匹配时给出明确诊断。
- `ways_to` 在任何用例执行前可反查完整的已声明入口，不产生浏览器副作用。
- 每个具体用例类仅收集一个继承的 test_process，按 init/setup/process/teardown 执行。
- init/setup 失败时跳过 process 并执行 teardown，各阶段失败保留原异常及可用证据。
- 清理失败、截图失败或驱动创建失败不会泄漏已有资源，已提交的业务动作不会自动重放。
- 数据初始化可重复执行，写入失败回滚，不将密码写入 SQLite 或步骤日志。
