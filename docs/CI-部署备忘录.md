# UITest 持续集成（Jenkins + Docker）部署备忘录

> 生成时间：2026-08-05
> 目的：PC 重启后继续 Jenkins 持续集成部署，本文档记录当前进度与后续步骤。

## 一、任务背景

将自动化测试工程 `G:\Project\UITest`（pytest + selenium/appium + allure 的 UI 自动化框架）接入 Jenkins 持续集成，Jenkins 通过 Docker 部署。工程保持在 `G:\Project\UITest`（不移动）。流水线内容：测试 + Allure 报告 + 构建通知。

## 二、环境现状（重启前已确认）

| 项目 | 状态 |
| --- | --- |
| 系统 | Windows，PowerShell 5.1 |
| Java | 23.0.1（已装，满足 Jenkins 要求） |
| Docker | **未安装**，用户需重启 PC 后安装 |
| Jenkins | 未安装、8080 端口未监听 |
| 工程 | `G:\Project\UITest`，git 仓库（分支 master，远程 406w/master），已有 `.venv` |
| Python | 系统 `G:\Python\python.exe`（3.12），工程 venv `G:\Project\UITest\.venv\Scripts\python.exe` |
| allure CLI | 本机未安装（报告生成待定，见"注意事项"） |

## 三、已完成的工作

### 1. Allure 报告路径修复（已生效）
- **问题**：`pytest.ini` 的 `--alluredir=report/allure-results` 是相对路径，从 `testcase` 目录运行时报告落到 `G:\Project\UITest\testcase\report\`。
- **修改**：
  - `pytest.ini`：移除 `--alluredir` 参数（addopts 不支持 `%(here)s` 变量替换）
  - `conftest.py`：新增 `pytest_configure` hook，基于 `conftest.py` 所在目录拼出绝对路径 `report/allure-results` 并写入 `config.option.allure_report_dir`
- **验证**：用例通过，结果固定写入 `G:\Project\UITest\report\allure-results\`

### 2. 移除 PR 层（page/page_redirect），跳转改为 PE 层装饰器（已生效）
- **删除**：`G:\Project\UITest\page\page_redirect\` 整个目录（4 个文件）
- **修改** `page/page_elements/locator.py`：
  - 新增 `jump(target, cond="", desc="")` 控件类装饰器（目标页面以字符串类名标注，避免模块循环导入）
  - **支持多条件跳转**：同一控件可堆叠多个 `@jump("PageA", cond="未登录", ...)` + `@jump("PageB", cond="已登录", ...)`
  - 跳转数据存在控件类 `_jump_targets`（list of (目标类名, 条件, 描述)）
  - `Page` 基类新增 `ways_to(target, cond=None)` / `ways_from(source, cond=None)` / `print_ways_to(target, cond=None)`
  - **返回元组为 4 元素**：`(描述, 跳转条件, 来源页面类, 来源控件类)`
- **修改** PE 页面类：
  - `bilibili_home_page.py`：`login_entry`、`go_login_btn` 加 `@jump("BilibiliLoginPage", ...)`
  - `bilibili_login_page.py`：`back_btn`、`login_btn` 加 `@jump("BilibiliHomePage", ...)`
  - 两文件 import `jump`（`page/page_elements/__init__.py` 已导出）
- **修改** PO 层（元组下标 1→2，解包加 cond）：
  - `page/page_objects/bilibili_home_page_object.py`：`go_to_login()` 用 `Page.ways_to(...)`，`w[2] is self.page`
  - `page/page_objects/bilibili_login_page_object.py`：`go_home()` 同理，`desc, cond, from_page, locator = login_ways[0]`
- **修改** 文档：`UITest.md`、`docs/UITest-框架实现详解.md` 已同步；`testcase/test_bilibili_login.py` 注释/标题更新
- **验证**：`python -c "from page.page_elements import BilibiliHomePage, BilibiliLoginPage, Page; print(Page.ways_to(BilibiliLoginPage))"` 输出 2 种方式；`pytest testcase/test_bilibili_login.py` 2 个用例全通过（18.53s）

### 3. CI 无头模式支持（已生效）
- **修改** `conftest.py`：
  - `pytest_addoption` 新增 `--headless`（store_true）
  - `driver` fixture 将 `headless` 传给 `driver_manager.create_driver(...)`
- **验证**：`pytest -m web --headless --browser chrome testcase/test_bilibili_login.py::test_bilibili_homepage_login_status` 通过（169.57s，首次含 ChromeDriver 下载）

### 4. Jenkinsfile（已写好，未在 Jenkins 中运行）
- 文件：`G:\Project\UITest\Jenkinsfile`
- 内容：Pipeline 声明式，4 阶段：
  1. 检出工程（echo 工作目录）
  2. 依赖安装：重建 `.venv` + `pip install -r requirements.txt`
  3. 执行 Web 测试：`pytest -m web --headless --browser chrome -q`
  4. 生成 Allure 报告：`$env:ALLURE_CLI generate ...` + publishHTML 归档（**依赖环境变量 ALLURE_CLI**，未配置时跳过归档）
- 通知：post 块留 emailext 注释扩展点，未启用
- 注意：PowerShell 块用单引号 `'''...'''` 包裹避免 Groovy 插值

## 四、下一步待办（重启安装 Docker 后）

1. **安装 Docker Desktop**（用户自行完成），确认 `docker version` 可用
2. **启动 Jenkins 容器**：
   ```powershell
   docker run -d --name jenkins -p 8080:8080 -p 50000:50000 `
     -v jenkins_home:/var/jenkins_home `
     -v G:/Project/UITest:/var/jenkins_data/UITest `
     jenkins/jenkins:lts
   ```
   注：Windows 盘符挂载路径为 `/G/Project/UITest`（docker run 在 Windows 上 `-v G:/Project/UITest:...` 的写法按 Docker Desktop 提示调整）
3. **解锁 Jenkins**：打开 `http://localhost:8080`，从容器读取初始密码：
   ```powershell
   docker exec jenkins cat /var/jenkins_home/secrets/initialAdminPassword
   ```
4. **安装插件**（按提示装 suggested，另需确认）：Pipeline、HTML Publisher、Allure Jenkins Plugin（可选）
5. **新建 Pipeline Job**：
   - 名称建议 `UITest-CI`
   - SCM 选 Git，仓库 `G:/Project/UITest`（或工程 git 远程 URL）
   - Pipeline 定义选 "Pipeline script from SCM"（Jenkinsfile 在工程根目录）
6. **配置 Allure 报告**（二选一）：
   - 方案 A：宿主安装 allure CLI 并设置 Jenkins 全局环境变量 `ALLURE_CLI`（指向 `allure.bat` 绝对路径）
   - 方案 B：Docker 内装 allure：`docker exec jenkins curl -o /tmp/allure.tgz ...`（较繁琐，推荐 A）
   - 本机当前**未安装** allure CLI，需下载：`https://github.com/allure-framework/allure2/releases` 解压到 `G:\Python\allure`，PATH 加 `G:\Python\allure\bin`
7. **构建触发方式**：可设置定时（如 `H 9 * * *` 每日 9 点）或手动触发
8. **验证**：手动触发构建，确认测试执行、Allure 报告归档、状态通知

## 五、注意事项 / 坑点

- 用例默认 `--browser edge`（Windows 本机），CI 中 Jenkinsfile 已显式指定 `--browser chrome`（无头）
- webdriver-manager 首次运行会下载浏览器驱动（已下载缓存于 `C:\Users\19469\.wdm`），CI 容器内需确保可联网下载；若失败可考虑将 `--browser chrome` 缓存路径挂载进容器
- 重启 PC 前建议先把 `G:\Project\UITest` 的改动 commit（当前有未提交修改：Jenkinsfile、conftest.py、locator.py、页面类、PO、文档）
- 测试工程 pytest.ini 有 `testpaths = testcase`、`pythonpath = .`，pip 安装依赖时注意从工程根目录执行
- Docker Desktop 重启后可能需要手动启动；若使用 WSL2 后端，检查 WSL 状态
