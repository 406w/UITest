"""Driver 工厂：统一创建 Web(selenium) / Android / IOS(appium) 驱动。

平台常量：
    platform="web"     -> selenium webdriver（chrome/edge/firefox）
    platform="android" -> appium AndroidDriver
    platform="ios"     -> appium IosDriver
"""
from __future__ import annotations

from typing import Any

from selenium import webdriver as selenium_webdriver


class UnsupportedPlatformError(ValueError):
    """不支持的平台。"""


class WebDriverFactory:
    WEB = "web"
    ANDROID = "android"
    IOS = "ios"
    SUPPORTED = (WEB, ANDROID, IOS)

    _EDGE_BROWSER = "edge"
    _CHROME_BROWSER = "chrome"
    _FIREFOX_BROWSER = "firefox"

    def __init__(self, platform: str = WEB, browser: str = _EDGE_BROWSER):
        if platform not in self.SUPPORTED:
            raise UnsupportedPlatformError(
                f"不支持的平台: {platform}，可选: {', '.join(self.SUPPORTED)}"
            )
        self.platform = platform
        self.browser = browser

    @property
    def platform_name(self) -> str:
        return {
            self.WEB: "web",
            self.ANDROID: "Android",
            self.IOS: "iOS",
        }[self.platform]

    def create(self, **kwargs: Any):
        if self.platform == self.WEB:
            return self._create_web(**kwargs)
        return self._create_appium(**kwargs)

    # ---------------- Web ----------------
    def _create_web(self, headless: bool = False, **_: Any):
        if self.browser == self._EDGE_BROWSER:
            from selenium.webdriver.edge.options import Options as EdgeOptions
            from selenium.webdriver.edge.service import Service as EdgeService
            from webdriver_manager.microsoft import EdgeChromiumDriverManager

            options = EdgeOptions()
            if headless:
                options.add_argument("--headless=new")
            options.add_argument("--start-maximized")
            return selenium_webdriver.Edge(
                service=EdgeService(EdgeChromiumDriverManager().install()),
                options=options,
            )

        if self.browser == self._CHROME_BROWSER:
            from selenium.webdriver.chrome.options import Options as ChromeOptions
            from selenium.webdriver.chrome.service import Service as ChromeService
            from webdriver_manager.chrome import ChromeDriverManager

            options = ChromeOptions()
            if headless:
                options.add_argument("--headless=new")
            options.add_argument("--start-maximized")
            return selenium_webdriver.Chrome(
                service=ChromeService(ChromeDriverManager().install()),
                options=options,
            )

        if self.browser == self._FIREFOX_BROWSER:
            from selenium.webdriver.firefox.options import Options as FirefoxOptions
            from selenium.webdriver.firefox.service import Service as FirefoxService
            from webdriver_manager.firefox import GeckoDriverManager

            options = FirefoxOptions()
            if headless:
                options.add_argument("--headless")
            options.add_argument("--start-maximized")
            return selenium_webdriver.Firefox(
                service=FirefoxService(GeckoDriverManager().install()),
                options=options,
            )

        raise UnsupportedPlatformError(f"不支持的浏览器: {self.browser}")

    # ---------------- Android / IOS ----------------
    def _create_appium(
        self,
        appium_server: str = "http://127.0.0.1:4723",
        desired_capabilities: dict[str, Any] | None = None,
        **_: Any,
    ):
        caps = dict(desired_capabilities or {})
        caps.setdefault("platformName", self.platform_name)
        caps.setdefault("automationName", "UiAutomator2" if self.platform == self.ANDROID else "XCUITest")
        if self.platform == self.ANDROID:
            from appium import webdriver as appium_webdriver

            return appium_webdriver.Remote(appium_server, caps)
        if self.platform == self.IOS:
            from appium import webdriver as appium_webdriver

            return appium_webdriver.Remote(appium_server, caps)
        raise UnsupportedPlatformError(f"不支持的平台: {self.platform}")
