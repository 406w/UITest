"""Driver 工厂：统一创建 Web(selenium) / Android / IOS(appium) 驱动。

平台常量：
    platform="web"     -> selenium webdriver（chrome/edge/firefox）
    platform="android" -> appium AndroidDriver
    platform="ios"     -> appium IosDriver

DriverManager：按名称管理多个驱动，一个用例可同时控制多个 web 页面 / 移动设备。
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
        from appium import webdriver as appium_webdriver

        if self.platform == self.ANDROID:
            from appium.options.android import UiAutomator2Options

            options = UiAutomator2Options()
        elif self.platform == self.IOS:
            from appium.options.ios import XCUITestOptions

            options = XCUITestOptions()
        else:
            raise UnsupportedPlatformError(f"不支持的平台: {self.platform}")

        caps = dict(desired_capabilities or {})
        caps.setdefault("platformName", self.platform_name)
        caps.setdefault(
            "automationName",
            "UiAutomator2" if self.platform == self.ANDROID else "XCUITest",
        )
        for key, value in caps.items():
            options.set_capability(key, value)
        return appium_webdriver.Remote(appium_server, options=options)


class DriverManager:
    """多设备驱动管理：按名称注册/获取/关闭多个 driver，支持一个用例同时控制多个 web 页面 / 移动设备。"""

    def __init__(self, page_load_timeout: float = 30.0):
        self.page_load_timeout = page_load_timeout
        self._drivers: dict[str, Any] = {}

    def create_driver(
        self,
        name: str = "main",
        platform: str = WebDriverFactory.WEB,
        browser: str = WebDriverFactory._EDGE_BROWSER,
        **kwargs: Any,
    ):
        """创建并注册一个驱动，返回 driver。name 重复时抛 ValueError。"""
        if name in self._drivers:
            raise ValueError(f"驱动已存在: {name}，已创建: {list(self._drivers)}")
        driver = WebDriverFactory(platform=platform, browser=browser).create(**kwargs)
        if platform == WebDriverFactory.WEB:
            driver.set_page_load_timeout(self.page_load_timeout)
        else:
            driver.implicitly_wait(10)
        self._drivers[name] = driver
        return driver

    def get_driver(self, name: str = "main"):
        """获取已注册的驱动。"""
        try:
            return self._drivers[name]
        except KeyError:
            raise ValueError(
                f"驱动不存在: {name}，已创建: {list(self._drivers)}"
            ) from None

    def close_driver(self, name: str) -> None:
        """关闭指定驱动并移除注册。"""
        driver = self._drivers.pop(name, None)
        if driver is not None:
            try:
                driver.quit()
            except Exception:
                pass

    def close_all(self) -> None:
        """关闭全部驱动。"""
        for name in list(self._drivers):
            self.close_driver(name)

    @property
    def drivers(self) -> dict[str, Any]:
        """当前存活的驱动：{名称: driver}。"""
        return self._drivers

    def __enter__(self) -> "DriverManager":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close_all()
