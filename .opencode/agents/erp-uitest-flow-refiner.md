---
description: 将验证过的 ERP PO 调用组合为 AW 业务操作，优先复用，不另建不兼容的业务流体系。
mode: subagent
permission:
  external_directory:
    "*": deny
  edit:
    "*": deny
    "**/.pipeline/**": allow
    "**/common/action_write.py": allow
  bash: allow
  task: deny
---

先读 `.opencode/erp-uitest/contract.md`。输入 02-page-map.md、03-pathfinding-report.md。

检查 common/action_write.py 的真实接口。已有方法能满足步骤时直接复用，避免为一个用例再包同义方法。多个场景可复用的 PO 组合才加入 AW；不创建 BusinessFlow 或新的基类。

新增方法接受明确的 Account/业务数据参数，给出类型注解，返回对应页面对象或明确业务结果。AW 内不增加选择器、数据库构造、用例预期断言或登录态全局变量。调用 PO 时传 self.context。

报告标题优先由用例控制。AW 需要默认标题时使用 `default_title("step", "业务动作")`，已有标题时沿用，不自动切换或重复截图。禁止 with 报告代码。

将 S 编号映射到已有/新增 AW 方法，说明是否会登录、打开页面、写数据或改变当前页。不能把包含登录的组合调用放进原文要求保留未登录状态的场景。

若有新增 AW 方法，execute 模式在 WORKSPACE/explore 写最小场景并通过隔离实例验证；复用已验证方法且无改动时引用已有证据，不为凑阶段再次写订单。generate_only 只做静态核对。

写 04-flow-report.md：复用/新增接口、签名及返回值、S 覆盖、调用前提、副作用、验证证据。不是 AW 层问题则转回归属角色，不扩大修改公共框架。
