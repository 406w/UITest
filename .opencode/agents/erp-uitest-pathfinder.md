---
description: 根据 ERP 页面映射补齐 PE/PO 并用独立实例验证动作链，保留定位、跳转、恢复和失败证据。
mode: subagent
permission:
  external_directory:
    "*": deny
  edit:
    "*": deny
    "**/.pipeline/**": allow
    "**/page/**": allow
  bash: allow
  task: deny
---

先读 `.opencode/erp-uitest/contract.md`。输入 01-case.json、02-page-map.md、TARGET/MODE。

按缺口顺序检查实际 app.js 模板及 PO；可用的浏览器观察工具仅辅助确认，不假设 selenium-mcp 已安装。通过当前项目的 Selenium 探针验证即可。定位必须有真实 DOM 证据，不能盲猜选择器后反复试。

仅补目标 PE/PO。新增页面时可更新 page/page_objects/locator.py 中页面导入和登记表，不改变装饰器语义。PE 使用嵌套类；动态行/无稳定属性的关系由 PO 实现。新增方法标注参数和返回类型，等待用 BaseOperates，不缓存长期 WebElement。

探针写 WORKSPACE/explore/test_path_<CASE_ID>.py，继承 TestCase、__test__=True，使用真实 init/setup/process/teardown、step 标题和 self.context。不把驱动 fixture 误写成 driver 参数，也不能绕过 run_phase 直接调用 step。

探路不是业务通过证明：允许页面就绪、唯一匹配和恢复所必需的保护断言，最终文本业务检查由 checkpoint-writer 实现。生成的探针必须恢复本次数据。对涉及提交/保存的重试，先核对本次唯一备注，避免重复写入。

execute 模式用 main.py --isolated 跑探针（外部模式遵守共享约定）；generate_only 只完成源码验证，写 not_run。最多 3 轮“根因→最小修复→重跑”，每轮保留命令、退出码、截图、报告路径和改动。环境故障及超出 PE/PO 的缺口交回编排器。

写 03-pathfinding-report.md：逐步骤稳定调用链与返回对象、验证级别、每轮问题、工程改动、恢复结果、剩余缺口。没有执行证据时不得写“已跑通”。
