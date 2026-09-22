# 文本用例 → ERP-UITest 脚本

参考 `G:/AI/.config/opencode/agent` 的入口、总编排与八角色分工，针对本工程重新编写。文件在项目内，不修改全局 agent 集合，也不改变现有测试框架。

## 使用

从当前仓库根目录打开 OpenCode，选择主 agent `erp-uitest-pipeline`，发送：

```text
请根据 .opencode/erp-uitest/examples/login_logout.case.md 生成用例。
CASE_ID=login_logout
MODE=execute
TARGET=isolated
按照完整流水线生成、审核、验证，并交付脚本和本次 Allure 报告。
```

只需要生成与静态验证时改成 `MODE=generate_only`。也可以把文本直接贴给 `erp-uitest` 入口，由它交给总编排。增加订单的输入见 [销售订单示例](examples/add_sale.case.md)。同名脚本已存在时说明是继续修改还是使用新 CASE_ID，避免覆盖现有成果。

## 角色与顺序

| Agent | 职责 | 主要产物 |
|---|---|---|
| erp-uitest | 入口与任务分流 | 规范化任务 |
| erp-uitest-pipeline | 串行编排、状态、交付门槛 | pipeline-state.json、10-delivery.md |
| erp-uitest-case-analyzer | 拆解前置、步骤、预期、恢复 | 01-steps.md、01-case.json |
| erp-uitest-page-mapper | 核对真实 PE/PO/AW 能力 | 02-page-map.md |
| erp-uitest-pathfinder | 探路与补页面能力 | 03-pathfinding-report.md、探路脚本 |
| erp-uitest-flow-refiner | 复用或补充 AW | 04-flow-report.md |
| erp-uitest-script-generator | 编写四阶段面向对象用例 | 测试脚本、05-generator-report.md |
| erp-uitest-checkpoint-writer | 补全真实断言 | 06-checkpoint-report.md |
| erp-uitest-consistency-checker | 运行前及调试后独立复核 | 07-consistency-report.md、09-final-consistency.md |
| erp-uitest-script-debugger | 收集、运行、有限修复、报告核对 | 08-debug-report.md、逐轮证据 |

角色定义见 [agents 目录](../agents)。输入快照、中间结果和报告保存在 `.pipeline/<CASE_ID>/<RUN_ID>/`；最终脚本在 `testcase/test_<CASE_ID>.py`。`.pipeline` 不纳入版本控制，防止误提交业务输入和运行记录。

## 工程约束

所有角色共用 [contract.md](contract.md)，阶段报告与状态模板分别为 [stage-report.template.md](stage-report.template.md) 和 [pipeline-state.template.json](pipeline-state.template.json)。

- 用例继承 TestCase，使用 init/setup/process/teardown；不定义构造函数，不重新绑定 fixture 已提供的资源。
- 使用 `step(标题)` / `checkpoint(标题)` 后直接写动作或断言。开始截图由现有框架产生，调试角色核对它出现在本次 Allure 产物中。
- PE 使用页面内嵌元素声明类；复用当前 PO/AW，不引入参考工程里的 BusinessFlow、移动平台分支或旧检查点接口。
- 未补齐断言的草稿禁止收集；静态完成、真实运行成功、报告生成成功分别记录。
- 默认隔离实例；订单以唯一备注追踪并恢复，框架与被测 ERP 源码默认只读。
- 账号按 YAML 与环境变量读取；每次检查真实代码，不能把管理员冒充其他角色。

## 配置兼容与验证边界

Markdown frontmatter 使用参考集合的 `permission`、`bash`、`task` 方言，不指定模型，继承使用者配置。项目路径采用 [OpenCode agents 文档](https://dev.opencode.ai/docs/agents/) 的 `.opencode/agents/`；权限按 [权限文档](https://dev.opencode.ai/docs/permissions/) 的后匹配覆盖规则，将通配 deny 放在具体 allow 之前。

OpenCode V2 文档使用不同的 `permissions` / `shell` / `subagent` 配置；本集合不混用两种语法。若使用 V2，先根据实际安装版本迁移配置后再运行，不把这些文件直接视为 V2 配置。

编写环境未发现 opencode 命令，因此此处能验证 Markdown frontmatter、角色引用、路径与模板，不能证明实际 OpenCode 调度已成功。需在安装了匹配方言的 OpenCode 中按上述示例完成首次验收。edit 权限也不等于 shell 文件沙箱；执行角色必须同时遵守共享约定的写入边界。

角色权限采用仓库内相对 glob，不依赖作者的 G 盘路径；外部目录默认拒绝。若文本文件在仓库外，可直接粘贴文本或按工具提示单独授权读取。
