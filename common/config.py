from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlsplit


@dataclass(frozen=True)
class Config:
    base_url: str = "http://localhost:8090"
    browser: str = "edge"
    headless: bool = True
    timeout: float = 10
    poll_interval: float = 0.15
    page_load_timeout: float = 30
    screenshots: bool = True
    click_snapshots: bool = False
    driver_path: str | None = None
    browser_binary: str | None = None
    remote_url: str | None = None

    def __post_init__(self):
        if urlsplit(self.base_url).scheme not in {"http", "https"}:
            raise ValueError("base_url 必须是 HTTP(S) 地址")
        if self.browser not in {"edge", "chrome", "firefox"}:
            raise ValueError("browser 必须为 edge/chrome/firefox")
        if self.remote_url and urlsplit(self.remote_url).scheme not in {"http", "https"}:
            raise ValueError("remote_url 必须是 HTTP(S) 地址")
        if min(self.timeout, self.poll_interval, self.page_load_timeout) <= 0:
            raise ValueError("等待时间必须大于 0")


@dataclass
class Context:
    config: Config
    nodeid: str = ""
    driver: object = None
    evidence_phases: set = field(default_factory=set)
    phase: str = "setup"
    secrets: set = field(default_factory=set, repr=False)

    def redact(self, text):
        value = str(text)
        for secret in sorted(self.secrets, key=len, reverse=True):
            if secret:
                value = value.replace(secret, "***")
        return value


ROOT = Path(__file__).resolve().parents[1]
