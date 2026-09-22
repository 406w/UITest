"""所有 pytest 启动方式共用的 Allure 输出配置。"""
from dataclasses import dataclass
from datetime import datetime
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
from uuid import uuid4

import pytest

from common.config import ROOT


@dataclass
class ReportRun:
    root: Path
    results: Path
    html: Path
    run_id: str
    generate_html: bool
    cli: str
    html_ready: bool = False
    error: str = ""


REPORT_RUN = pytest.StashKey[ReportRun]()


def add_report_options(parser):
    parser.addini("erp_report_dir", "报告根目录，相对于工程根目录", default="report")
    parser.addini("erp_report_html", "测试结束后生成 Allure HTML", type="bool", default=True)
    parser.addini("erp_allure_cli", "Allure CLI 路径；也可使用 ALLURE_CLI 或 PATH", default="")
    group = parser.getgroup("erp-report")
    group.addoption("--report-html", dest="report_html", action="store_true", default=None)
    group.addoption("--no-report-html", dest="report_html", action="store_false", default=None)
    group.addoption("--allure-cli", default=None, help="Allure CLI 可执行文件路径")


@pytest.hookimpl(tryfirst=True)
def pytest_configure(config):
    # 必须先于 allure-pytest 注册文件写入器设置目录。
    if config.option.collectonly:
        return
    if not hasattr(config.option, "allure_report_dir"):
        raise pytest.UsageError("缺少 allure-pytest，请安装 requirements.lock.txt 中的依赖")
    root = Path(config.getini("erp_report_dir"))
    if not root.is_absolute():
        root = ROOT / root
    root = root.resolve()
    run_id = datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + uuid4().hex[:8]
    explicit_results = config.option.allure_report_dir
    if explicit_results:
        # 显式 --alluredir 保持 pytest 原有相对工作目录的语义。
        results = Path(explicit_results).resolve()
        if results.parent == root / "allure-results" and re.fullmatch(r"\d{8}-\d{6}-[0-9a-f]+", results.name):
            run_id = results.name
    else:
        results = root / "allure-results" / run_id
    results.mkdir(parents=True, exist_ok=True)
    config.option.allure_report_dir = str(results)
    html_option = config.getoption("report_html")
    generate_html = config.getini("erp_report_html") if html_option is None else html_option
    cli = config.getoption("allure_cli") or os.getenv("ALLURE_CLI") or config.getini("erp_allure_cli")
    if not cli:
        cli = shutil.which("allure") or shutil.which("allure.bat") or ""
    config.stash[REPORT_RUN] = ReportRun(root, results, root / "allure-report" / run_id,
                                       run_id, generate_html, cli)


@pytest.hookimpl(trylast=True)
def pytest_sessionfinish(session, exitstatus):
    config = session.config
    if REPORT_RUN not in config.stash or hasattr(config, "workerinput"):
        return
    report = config.stash[REPORT_RUN]
    if report.generate_html:
        try:
            if not report.cli:
                raise FileNotFoundError("未找到 Allure CLI，请配置 erp_allure_cli、ALLURE_CLI 或 --allure-cli")
            process = subprocess.run(
                [report.cli, "generate", str(report.results), "-o", str(report.html)],
                cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace",
                timeout=60, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            report.html_ready = process.returncode == 0 and (report.html / "index.html").is_file()
            if not report.html_ready:
                raise RuntimeError(f"Allure generate 返回 {process.returncode}：{process.stdout}\n{process.stderr}")
        except (OSError, RuntimeError, subprocess.TimeoutExpired) as error:
            report.error = str(error)
    # 无论测试通过还是失败，都保留路径与测试退出状态，不用报告错误覆盖测试错误。
    metadata = {
        "run_id": report.run_id,
        "pytest_exit_status": int(exitstatus),
        "results": str(report.results),
        "html": str(report.html / "index.html") if report.html_ready else None,
        "html_requested": report.generate_html,
        "report_error": report.error or None,
    }
    try:
        report.root.mkdir(parents=True, exist_ok=True)
        temporary = report.root / f".latest-{uuid4().hex}.json"
        temporary.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(report.root / "latest.json")
    except OSError as error:
        report.error += f"\n无法写入报告索引：{error}"


def pytest_terminal_summary(terminalreporter, exitstatus, config):
    if REPORT_RUN not in config.stash:
        return
    report = config.stash[REPORT_RUN]
    terminalreporter.section("Allure 报告")
    terminalreporter.write_line(f"原始结果：{report.results}")
    if report.html_ready:
        terminalreporter.write_line(f"HTML 报告：{report.html / 'index.html'}")
        prefix = f'& "{report.cli}"' if os.name == "nt" else f'"{report.cli}"'
        terminalreporter.write_line(f'打开命令：{prefix} open "{report.html}"')
    elif report.error:
        terminalreporter.write_line(f"HTML 未生成（原始结果已保留）：{report.error}", red=True)
    else:
        terminalreporter.write_line("HTML 自动生成已关闭，可用 --report-html 开启。")
    terminalreporter.write_line(f"本次报告索引：{report.root / 'latest.json'}")
