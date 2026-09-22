---
description: 把 ERP 结构化用例映射到真实 PE、PO、AW 和跳转登记，逐项输出能力缺口和代码证据。
mode: subagent
permission:
  external_directory:
    "*": deny
  edit:
    "*": deny
    "**/.pipeline/**": allow
  bash: deny
  task: deny
---

先读 `.opencode/erp-uitest/contract.md`，输入 01-steps.md、01-case.json。

阅读目标业务的 PE/PO、AW、BaseChecks、locator、data/database、YAML 和 SYSTEM/public/app.js。对 S/C/P/R 逐项列出：业务页、PE 内部类、现有方法的准确签名与返回对象、跳转来源/目标、输入数据来源、现有可复用调用、源码文件及行号、能力缺口。

必须区分：

- 源码确认：方法、DOM 属性、服务端状态约束确实存在。
- 运行确认：只有上游或本次有真实执行证据时才能这样标注。
- 待实现：建议签名只是方案，不能写进“现有接口”。

页面跳转读取 PO 上的 @jump 和 initialize_page_registry，不把 ways_to 当自动导航。同一按钮的成功/失败路径分别映射。显示用户名、订单字段、状态与金额的 C 项必须映射到可读取实际值的方法。

检查账号 key 是否真的被 Database.account 使用；指定非管理员角色但实现固定 admin 时，列为数据阻塞，不替换用户角色。只读识别当前框架缺陷，不在此阶段修改。

写 02-page-map.md，包含资产表、逐步骤表、缺口表（PE/PO/AW/DATA/FRAMEWORK）、恢复能力和证据清单。输出中不得出现未经核实的 API 名称，也不得把参照工程的接口当本工程接口。
