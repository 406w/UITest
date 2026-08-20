# UITest 持续集成（Jenkins + Docker）部署备忘录

> 生成时间：2026-08-05，更新：2026-08-20（部署完成）
> 目的：记录 Jenkins 持续集成的实际架构、部署过程与运维要点，PC 重启后可按此恢复。

## 一、任务背景

将自动化测试工程 `G:\Project\UITest`（pytest + selenium/appium + allure 的 UI 自动化框架）接入 Jenkins 持续集成，Jenkins 通过 Docker 部署。工程保持在 `G:\Project\UITest`（不移动）。流水线内容：测试 + Allure 报告 + 构建通知。

## 二、实际架构（2026-08-20 已落地）

| 组件 | 说明 |
| --- | --- |
| Jenkins master | Docker 容器 `jenkins`（jenkins/jenkins:lts，版本 2.568.2），端口 8080（Web）+ 50000（JNLP） |
| 执行节点 | Windows 宿主 agent `windows`（JNLP），remote FS `C:\Users\19469\jenkins-agent`，label `windows`，1 executor |
| 容器持久化 | volume `jenkins_home:/var/jenkins_home`（含宿主 SSH key `~/.ssh`，已拷入容器供 GitHub 克隆） |
| 运行方式 | 容器 `--restart unless-stopped` 开机自启；agent 登录自启（用户注册表 Run 键 `JenkinsAgent`，脚本 `C:\Users\19469\jenkins-agent\start_agent.ps1`） |
| 测试执行 | 流水线在 Windows agent 上跑：重建 `.venv` + `pytest -m web --headless --browser chrome` |
| 报告 | 宿主 allure CLI 2.45.0（`G:\Python\allure\allure-2.45.0`），Jenkins 全局环境变量 `ALLURE_CLI = G:\Python\allure\allure-2.45.0\bin\allure.bat`，htmlpublisher 归档 |

## 三、Jenkins 初始化记录

- **管理员**：`admin`，密码存于 `C:\Users\19469\AppData\Local\Temp\opencode\jenkins_admin.txt`
- **插件**：git、workflow-aggregator（Pipeline）、pipeline-stage-view、htmlpublisher、timestamper 及依赖
- **Job**：`UITest-CI`，SCM `git@github.com:406w/UITest.git`，分支 `*/master`，scriptPath Jenkinsfile，lightweight=false
- **凭据**：`bilibili-test-account`（UsernamePassword，username=1767104317），供流水线初始化 CI 数据库
- **构建结果**：#7 起 SUCCESS；测试 3 passed / 1 skipped（滑块验证码）/ 1 deselected；Allure 报告归档于构建页 `Allure_20_e6b58b_e8af95_e68aa5_e5918a`

## 四、关键代码改动（已提交，分支 master）

| 提交 | 内容 |
| --- | --- |
| c9f9a3b | 接入 Jenkins CI：Jenkinsfile、headless 支持、Allure 路径修复、移除 PR 层（跳转改 PE 层装饰器） |
| 6deb601 | 修复 wait_loaded（首页改找 home_header，因 bilibili 网页版已无 #btn-account）；Jenkinsfile 加 init_db |
| 7165ab2 | Jenkinsfile 依赖安装阶段用凭据初始化 CI 测试数据库（writeFile 生成 data/init_db_ci.py，账号密码取自 credentials，避免真实账号入库） |
| ccfa3dd | 登录用例修复：账号未指定时取站点默认账号（business_flow.get_account 支持 None）；complete_login 方法名避开 PO 属性 self.login 冲突；登录触发滑块验证码时优雅跳过（pytest.skip） |

### 测试与数据约定
- `data/init_db.py` 与 `data/test_data.db` 被 .gitignore 排除（含真实账号，勿提交）；CI 用 Jenkinsfile 内联生成 `data/init_db_ci.py` + 凭据初始化
- 登录用例 `ACCOUNT_USERNAME` 从环境变量 `BILI_USERNAME` 读取，未设置时取 DB 站点默认账号（本地默认 autotest，CI 默认凭据账号）

## 五、运维命令速查

```powershell
# 启动/查看 Jenkins 容器
docker start jenkins
docker ps -a --filter name=jenkins
docker logs -f jenkins
# 初始密码（若重置）
docker exec jenkins cat /var/jenkins_home/secrets/initialAdminPassword
# 手动触发构建（浏览器打开即可，或用 API）
curl -u admin:<pwd> -X POST http://localhost:8080/job/UITest-CI/build
# 手动启动 agent（登录自启已配置，无需手动）
powershell -ExecutionPolicy Bypass -File C:\Users\19469\jenkins-agent\start_agent.ps1
# 报告地址
http://localhost:8080/job/UITest-CI/lastBuild/Allure_20_e6b58b_e8af95_e68aa5_e5918a/
```

## 六、坑点记录（重要）

- **PowerShell 5.1 传参丢双引号**：curl 的 JSON body 必须 `--data-binary "@file"` 方式发送
- **Jenkins 2.568.2 解锁/登录 API**：解锁页在 `/loginError`（带 `Jenkins-Crumb`）；登录后 crumb 失效，需从 `/crumbIssuer/api/json` 重取
- **config.xml POST 不能含非 ASCII 字符**：XSLT 按 Latin-1 读取报 `invalid XML character 0x8c`，description 用纯 ASCII
- **PS 5.1 字符串内嵌 `$i:` 或 `-join ','` 报解析错**：写成 `${i}:` 或先算变量
- **Jenkinsfile 的 @script 检出在 master 执行**：master 容器必须持有 GitHub SSH key（已配置）
- **bilibili 网页版已改版**：未登录态无 `#btn-account`，只有 `div.go-login-btn` / `div.header-login-entry`；登录提交会触发 geetest 滑块验证码，headless 无法完成，用例检测到验证码自动 skip
- **每个 bash 命令都要刷新 PATH**：`$env:Path = [Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [Environment]::GetEnvironmentVariable("Path","User")`，否则 docker 不可用
- **poll_build.ps1 的 ConvertFrom-Json 在响应含异常字符时可能崩**：直接 curl consoleText 更可靠