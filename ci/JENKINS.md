# Jenkins Docker 流水线

仓库：https://github.com/406w/UITest.git，分支 `main`。任务名 `UITest-CI`，读取根目录 Jenkinsfile。

## 架构

复用已有 Jenkins 控制器。Compose 创建专用 inbound agent、Selenium Chrome 和本机报告服务，控制器不运行本工程测试，不挂载宿主 Docker socket。测试节点标签 `erp-uitest-linux`，仅接收匹配该标签的任务，单执行器。容器通过独立 Compose 网络通信，不向宿主暴露 Selenium 端口。

节点镜像包含 Python 3.11、Node 24、Java 21 和 Allure 2.45.0；每次构建在工作区按 requirements.lock.txt 创建虚拟环境。镜像基础与浏览器使用固定 digest。

## 首次接入已有 Jenkins

1. 控制器安装 Pipeline、Git、JUnit、HTML Publisher、Timestamper 插件。
2. 创建 Permanent Agent：名字和标签为 `erp-uitest-linux`，远程目录 `/home/jenkins/agent`，执行器 1，Usage 选择仅匹配标签，启动方式选择 agent 主动连接 controller。
3. 将该节点页面的连接 secret 保存到 `ci/jenkins/secrets/agent-secret`（仅密钥文本，不加引号）。这个目录被 Git 和 Docker build context 排除，不放进 Jenkinsfile、参数或报告。
4. 仓库根目录执行 `docker compose -f ci/compose.yaml up -d --build`。Docker Desktop 默认通过 `host.docker.internal:8080` 连接已有控制器；其他地址使用环境变量 JENKINS_URL 覆盖。
5. 创建或更新 Pipeline 任务 `UITest-CI`，SCM URL 为 `https://github.com/406w/UITest.git`，分支 `*/main`，Script Path 为 `Jenkinsfile`。如仓库改为私有，应在 Jenkins SCM 中配置只读凭据。
6. 点击 Build Now。默认执行全部框架检查、登录、错误密码、退出登录、新增销售订单、新增采购订单。

## 隔离与报告

每次 UI 运行由 main.py 启动仓库自带 `demo/erp`，使用独立随机端口、数据库和演示数据，结束后停止 Node 进程。ERP 监听 agent 内部网卡，浏览器使用 `http://agent:<随机端口>`；现有 8090 ERP 的业务数据不参与测试。

ERP_ISOLATED_BIND_HOST/ERP_ISOLATED_PUBLIC_HOST 仅改变容器间地址。普通本机运行仍绑定 127.0.0.1。SELENIUM_REMOTE_URL 指向 Compose 内的浏览器；不设置时保留本机浏览器方式。

构建归档 JUnit、Allure JSON、PNG 开始截图、HTML 及 ci-verification.json。后者检查本次 UI 结果身份和截图存在性。失败时保留已有报告且构建不标记成功。HTML 位于构建页的 Allure UI 链接；如果浏览器受到 Jenkins CSP 限制，可下载归档用 `allure open` 打开，不关闭全局 CSP。

本机直接查看入口为 http://127.0.0.1:8082/ 。独立 Nginx 只提供工作区的 report/ui-html，禁止目录列表与符号链接，仅绑定 127.0.0.1，且只读挂载节点卷。该入口与 Jenkins 的 localhost:8080 不同源，不需要放宽 Jenkins CSP。首次构建前和清理工作区期间可能返回 404；历史报告始终从 Jenkins 构建归档下载。任务名若改变，需要同步修改 ci/nginx.conf 的 root 路径。

源码中只有隔离演示环境的初始数据；真实环境密码通过 ERP_TEST_PASSWORD 环境变量提供。Database.account 按 YAML key 取账号，不再固定返回管理员。demo/erp 是源工程服务代码快照，不包含任何本机运行数据库。

## 日常更新与恢复

推送 main 后手动 Build Now，不默认添加定时触发。修改节点镜像或 Compose 后重新执行 up -d --build；代码修改无需重建镜像。

`docker compose -f ci/compose.yaml down` 只停止这套 UI 测试容器；不要加 `-v`，保留节点工作区。不会停止原 Jenkins 控制器或现有 ERP。节点密钥仅用于此节点，删除节点或重建 Jenkins 后需更新 secret。

参考：[Jenkins Docker](https://www.jenkins.io/doc/book/installing/docker/)、[Jenkins agents](https://www.jenkins.io/doc/book/using/using-agents/)、[Selenium Grid](https://www.selenium.dev/documentation/grid/getting_started/)。
