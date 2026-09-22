pipeline {
    agent { label 'erp-uitest-linux' }
    options {
        skipDefaultCheckout(true)
        disableConcurrentBuilds()
        timeout(time: 30, unit: 'MINUTES')
        buildDiscarder(logRotator(numToKeepStr: '20', artifactNumToKeepStr: '10'))
        timestamps()
    }
    environment {
        PYTHONUTF8 = '1'
        PYTHONUNBUFFERED = '1'
        ALLURE_CLI = '/opt/allure/bin/allure'
        ALLURE_NO_ANALYTICS = '1'
        SELENIUM_REMOTE_URL = 'http://selenium:4444'
        ERP_ISOLATED_BIND_HOST = '0.0.0.0'
        ERP_ISOLATED_PUBLIC_HOST = 'agent'
    }
    stages {
        stage('Checkout') {
            steps {
                deleteDir()
                checkout scm
            }
        }
        stage('Dependencies') {
            steps {
                sh '''
                    python3 -m venv .venv
                    .venv/bin/python -m pip install --disable-pip-version-check -r requirements.lock.txt
                    .venv/bin/python -m pip check
                    node --version
                    "$ALLURE_CLI" --version
                '''
            }
        }
        stage('Framework checks') {
            steps {
                sh '.venv/bin/python -m pytest framework_checks -q --no-report-html --alluredir=report/framework-results --junitxml=report/framework-junit.xml --basetemp=.runtime/framework-temp'
            }
        }
        stage('UI scenarios') {
            steps {
                sh '.venv/bin/python main.py --isolated --browser chrome -q --tb=short --alluredir=report/ui-results --junitxml=report/ui-junit.xml'
            }
        }
    }
    post {
        always {
            script {
                int reportStatus = sh(returnStatus: true, script: '.venv/bin/python ci/verify_report.py')
                if (fileExists('report/framework-junit.xml')) {
                    junit testResults: 'report/*-junit.xml', allowEmptyResults: false
                }
                if (fileExists('report/ui-html/index.html')) {
                    publishHTML(target: [reportDir: 'report/ui-html', reportFiles: 'index.html', reportName: 'Allure UI', keepAll: true, alwaysLinkToLastBuild: true, allowMissing: false])
                }
                archiveArtifacts artifacts: 'report/**', allowEmptyArchive: true
                if (reportStatus != 0 && currentBuild.currentResult == 'SUCCESS') {
                    error('Allure 报告或步骤开始截图验证失败；已有产物已归档')
                }
            }
        }
    }
}
