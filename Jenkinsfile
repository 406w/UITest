pipeline {
    agent { label 'windows' }

    options {
        timestamps()
        buildDiscarder(logRotator(numToKeepStr: '20'))
        disableConcurrentBuilds()
    }

    environment {
        VENV_ACTIVATE  = "${WORKSPACE}/.venv/Scripts/python.exe"
        ALLURE_RESULTS = "${WORKSPACE}/report/allure-results"
        ALLURE_HTML    = "${WORKSPACE}/report/allure-report"
    }

    stages {
        stage('检出工程') {
            steps {
                echo "工作目录: ${WORKSPACE}"
            }
        }

        stage('依赖安装') {
            steps {
                powershell '''
                    if (Test-Path "$env:WORKSPACE\\.venv") { Remove-Item "$env:WORKSPACE\\.venv" -Recurse -Force }
                    & python -m venv "$env:WORKSPACE\\.venv"
                    & "$env:WORKSPACE\\.venv\\Scripts\\python.exe" -m pip install --upgrade pip -q
                    & "$env:WORKSPACE\\.venv\\Scripts\\python.exe" -m pip install -r requirements.txt -q
                '''
                script {
                    writeFile file: 'data/init_db_ci.py', text: '''# -*- coding: utf-8 -*-
import os
import sqlite3
from pathlib import Path

db = Path(os.environ["WORKSPACE"]) / "data" / "test_data.db"
conn = sqlite3.connect(db)
conn.executescript(
    "CREATE TABLE IF NOT EXISTS sites ("
    " id INTEGER PRIMARY KEY AUTOINCREMENT,"
    " name TEXT NOT NULL UNIQUE,"
    " url TEXT NOT NULL UNIQUE,"
    " created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')));"
    "CREATE TABLE IF NOT EXISTS accounts ("
    " id INTEGER PRIMARY KEY AUTOINCREMENT,"
    " site_id INTEGER NOT NULL,"
    " username TEXT NOT NULL,"
    " password TEXT NOT NULL,"
    " is_default INTEGER NOT NULL DEFAULT 0,"
    " created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),"
    " FOREIGN KEY (site_id) REFERENCES sites(id) ON DELETE CASCADE);"
)
site = conn.execute("SELECT id FROM sites WHERE name = ?", ("哔哩哔哩",)).fetchone()
if site is None:
    site_id = conn.execute(
        "INSERT INTO sites (name, url) VALUES (?, ?)",
        ("哔哩哔哩", "https://www.bilibili.com/"),
    ).lastrowid
else:
    site_id = site[0]
user = os.environ.get("BILI_USER")
pwd = os.environ.get("BILI_PWD")
if user and pwd:
    exists = conn.execute(
        "SELECT id FROM accounts WHERE site_id = ? AND username = ?",
        (site_id, user),
    ).fetchone()
    if exists is None:
        conn.execute(
            "INSERT INTO accounts (site_id, username, password, is_default) VALUES (?, ?, ?, 1)",
            (site_id, user, pwd),
        )
conn.commit()
conn.close()
print("CI 数据库初始化完成:", db)
'''
                }
                withCredentials([usernamePassword(
                    credentialsId: 'bilibili-test-account',
                    usernameVariable: 'BILI_USER',
                    passwordVariable: 'BILI_PWD'
                )]) {
                    powershell '''
                        & "$env:WORKSPACE\\.venv\\Scripts\\python.exe" data\\init_db_ci.py
                    '''
                }
            }
        }

        stage('执行 Web 测试') {
            steps {
                powershell '''
                    & "$env:WORKSPACE\\.venv\\Scripts\\python.exe" -m pytest -m web --headless --browser chrome -q
                '''
            }
        }

        stage('生成 Allure 报告') {
            steps {
                script {
                    if (env.ALLURE_CLI == null || env.ALLURE_CLI == '') {
                        echo '未配置 ALLURE_CLI 环境变量（allure 命令行工具绝对路径），跳过报告归档'
                    } else {
                        powershell '''
                            & "$env:ALLURE_CLI" generate report\\allure-results -o report\\allure-report --clean
                        '''
                        publishHTML(target: [
                            allowMissing         : true,
                            alwaysLinkToLastBuild: true,
                            keepAll              : true,
                            reportDir            : 'report/allure-report',
                            reportFiles          : 'index.html',
                            reportName           : 'Allure 测试报告'
                        ])
                    }
                }
            }
        }
    }

    post {
        always {
            echo "pipeline 完成，结果: ${currentBuild.currentResult}"
            // 通知在此扩展：配置邮件/企业微信/钉钉 webhook 凭据后取消下面注释即可
            // emailext(subject: "UITest 构建 ${currentBuild.currentResult}",
            //          body: "请查看 Allure 报告: ${BUILD_URL}allure",
            //          to: env.MAIL_TO)
        }
        success {
            echo '全部用例通过'
        }
        failure {
            echo '存在失败，请查看报告与测试日志'
        }
    }
}