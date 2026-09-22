import logging

from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.webdriver.firefox.service import Service as FirefoxService

log = logging.getLogger(__name__)


class DriverFactory:
    @staticmethod
    def create(config):
        types = {
            "edge": (webdriver.Edge, webdriver.EdgeOptions, EdgeService),
            "chrome": (webdriver.Chrome, webdriver.ChromeOptions, ChromeService),
            "firefox": (webdriver.Firefox, webdriver.FirefoxOptions, FirefoxService),
        }
        constructor, options_type, service_type = types[config.browser]
        options = options_type()
        options.unhandled_prompt_behavior = "ignore"
        if config.headless:
            options.add_argument("-headless" if config.browser == "firefox" else "--headless=new")
        if config.browser != "firefox":
            options.add_argument("--disable-gpu")
            options.add_argument("--no-first-run")
            options.add_argument("--disable-search-engine-choice-screen")
        if config.browser_binary:
            options.binary_location = config.browser_binary
        service = None if config.remote_url else (service_type(executable_path=config.driver_path) if config.driver_path else service_type())
        driver = None
        try:
            driver = (webdriver.Remote(command_executor=config.remote_url, options=options)
                      if config.remote_url else constructor(options=options, service=service))
            driver.implicitly_wait(0)
            driver.set_page_load_timeout(config.page_load_timeout)
            driver.set_script_timeout(config.timeout)
            driver.set_window_size(1440, 1000)
            return driver
        except BaseException:
            if driver is not None:
                try:
                    driver.quit()
                except Exception:
                    log.exception("驱动创建失败后的清理异常")
            try:
                if service is not None:
                    service.stop()
            except Exception:
                log.exception("停止驱动服务失败")
            raise

    @staticmethod
    def close(context):
        driver, context.driver = context.driver, None
        if driver is not None:
            try:
                driver.quit()
            except Exception:
                log.exception("关闭浏览器失败")

    @classmethod
    def reset(cls, context):
        cls.close(context)
        context.driver = cls.create(context.config)
