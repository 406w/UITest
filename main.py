"""运行 UI 用例，可用隔离的真实 ERP 服务验证。"""
import argparse
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import time
from urllib.request import urlopen
from uuid import uuid4

ROOT = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--isolated", action="store_true", help="启动独立 ERP 服务和数据库，结束后停止服务")
    parser.add_argument("--erp-root", type=Path, help="隔离 ERP 服务源码目录，默认使用仓库 demo/erp，兼容旧父目录")
    parser.add_argument("--html", action="store_true", help="显式启用 HTML 报告（默认由 pytest.ini 开启）")
    args, pytest_args = parser.parse_known_args()
    if args.html:
        pytest_args.append("--report-html")
    run_id = time.strftime("%Y%m%d-%H%M%S") + "-" + uuid4().hex[:6]
    output = ROOT / "report" / "allure-results" / run_id
    runtime = ROOT / ".runtime" / run_id
    runtime.mkdir(parents=True)
    if not any(arg.startswith("--basetemp") for arg in pytest_args):
        pytest_args += ["--basetemp", str(runtime / "pytest-temp")]
    pytest_args += ["-o", f"cache_dir={runtime / 'pytest-cache'}"]
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    env.setdefault("SE_CACHE_PATH", str(ROOT / ".runtime" / "selenium"))
    process, log_file = None, None
    try:
        if args.isolated:
            erp_root = (args.erp_root or (ROOT / "demo" / "erp" if (ROOT / "demo" / "erp" / "server.js").is_file() else ROOT.parent)).resolve()
            if not (erp_root / "server.js").is_file():
                raise FileNotFoundError(f"找不到隔离 ERP 服务：{erp_root / 'server.js'}")
            node = shutil.which("node")
            if not node:
                raise RuntimeError("隔离运行需要 Node.js 24 或更高版本")
            if any(arg.startswith("--base-url") for arg in pytest_args):
                raise ValueError("--isolated 不能同时指定 --base-url")
            with socket.socket() as sock:
                sock.bind(("127.0.0.1", 0))
                port = sock.getsockname()[1]
            env.update(PORT=str(port), DATA_DIR=str(runtime / "erp-data"), DEMO_MODE="false",
                       HOST=os.getenv("ERP_ISOLATED_BIND_HOST", "127.0.0.1"))
            # 仅隔离的演示数据实例使用项目自带初始密码。
            env["ERP_TEST_PASSWORD"] = "Erp123456!"
            log_file = (runtime / "server.log").open("w", encoding="utf-8")
            process = subprocess.Popen([node, "server.js"], cwd=erp_root, env=env,
                                       stdout=log_file, stderr=subprocess.STDOUT,
                                       creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            base_url = f"http://127.0.0.1:{port}"
            deadline = time.monotonic() + 20
            while True:
                if process.poll() is not None:
                    raise RuntimeError(f"ERP 服务启动失败，参见 {runtime / 'server.log'}")
                try:
                    with urlopen(base_url + "/api/health", timeout=1) as response:
                        if response.status == 200:
                            break
                except OSError:
                    pass
                if time.monotonic() >= deadline:
                    raise TimeoutError("隔离 ERP 服务启动超时")
                time.sleep(0.2)
            browser_url = f"http://{os.getenv('ERP_ISOLATED_PUBLIC_HOST', '127.0.0.1')}:{port}"
            pytest_args += ["--base-url", browser_url]
            print(f"隔离 ERP：{base_url}，数据库：{runtime / 'erp-data'}", flush=True)
        if not any(arg == "--alluredir" or arg.startswith("--alluredir=") for arg in pytest_args):
            pytest_args += ["--alluredir", str(output)]
        return subprocess.call([sys.executable, "-m", "pytest", *pytest_args], cwd=ROOT, env=env)
    finally:
        if process is not None:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
        if log_file:
            log_file.close()


if __name__ == "__main__":
    raise SystemExit(main())
