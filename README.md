# UITest 框架说明

基于 pytest + selenium + allure 的测试框架
能够实现 Web 系统的自动化测试

## 工程结构

文本用例转脚本的 OpenCode agent 集合见 [.opencode/erp-uitest/README.md](.opencode/erp-uitest/README.md)，包含总agent、8个任务子agent、脚本示例等。

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
│   │   └── order_page.py      
│   └── page_objects/          # PO 页面对象层（每个页面文件对应一个操作文件，输出页面元素对象，关联元素对象与其他页面的跳转关系）
│   │   ├── locator.py         # jump 跳转装饰器， ways_to 反查（查找元素对象与页面的跳转关系）
│   │   ├── home_po.py         # 链式调用，输出元素对象，关联元素对象与其他页面的跳转关系（对PE层仅声明描述的控件，在此处通过相对关系输出元素对象）
│   │   ├── login_po.py
│   │   └── order_po.py        
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
├── report/                    # 测试报告
    ├── allure-results/        # 原始结果（pytest --alluredir 生成）
    └── allure-report/         # HTML 报告（allure generate 生成）
├── ci/                    # 测试报告
    ├── allure-results/        # 原始结果（pytest --alluredir 生成）
└── main.py                    # 执行入口，可启动隔离 ERP 并生成报告
```
