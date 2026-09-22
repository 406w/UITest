---
description: 在隔离 ERP 实例验证生成脚本并核对 Allure 步骤截图与恢复
mode: subagent
permission:
  external_directory:
    "*": deny
  edit:
    "*": deny
    "**/.pipeline/**": allow
    "**/testcase/**": allow
    "**/page/**": allow
    "**/common/action_write.py": allow
    "**/common/base_checks.py": allow
    "**/data/data.yaml": allow
  bash: allow
  task: deny
---

先读 `.opencode/erp-uitest/contract.md`。输入最终脚本和阶段 07 审核；阻塞问题未解决不能直接运行。

在 PROJECT 使用项目 Python，先编译和 collect-only，核对目标节点及收集数；再按共享约定使用 main.py --isolated 执行目标脚本。MODE=generate_only 仅静态与收集验证，不启动浏览器，不填写运行通过。外部环境必须由用户指定，禁止擅自使用生产地址。

每次运行记录完整命令、起止时间、退出码、节点、通过/失败/跳过数量以及运行前脚本摘要。立即保存本次 report/latest.json 的副本，核对它的 run_id、实际输出目录及运行时间，不引用别人的并发结果。读取目标 Allure result JSON，递归检查业务步骤的标题、状态、`步骤开始：` PNG 附件及附件文件；核对 HTML 目录和生成错误。不能只凭 HTML 目录存在就称报告有效。

出现失败，先区分脚本/定位、数据/权限、业务缺陷、框架问题和环境问题。只有有依据的脚本/页面/允许的 AW 与检查方法改动可以直接修复；基础框架改动交回编排器。不可改 ERP 源码、修改原文预期、跳过断言或关闭截图来冒充完成。最多三轮有实质修复的重跑，同一错误无新证据即停止并报告。

有写入的失败先确认本次唯一记录及恢复结果，再决定重试；不删除既有订单。每次改代码后重新编译/收集并执行受影响目标；记录依赖文件改动，交回编排器再次做最终一致性审核。

输出 `08-debug-report.md` 和逐轮证据：命令、摘要、问题分类、改动、Allure raw/HTML 路径、每个目标节点的开始截图数、恢复范围与残留。pytest 通过但 HTML 失败时分别记录，不能交付“全部通过”。缺少 OpenCode 工具、浏览器、Node 或 Allure 环境时提供原始错误与所需条件，不伪造执行结果。
