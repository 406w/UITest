from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from common.config import Config
from common.driver import DriverFactory


def test_remote_browser_uses_grid_and_cleans_up_when_configuration_fails(monkeypatch):
    remote = Mock()
    browser = Mock()
    remote.return_value = browser
    local = Mock(side_effect=AssertionError('不能启动本机浏览器'))
    monkeypatch.setattr('common.driver.webdriver.Remote', remote)
    monkeypatch.setattr('common.driver.webdriver.Chrome', local)
    config = Config(browser='chrome', remote_url='http://selenium:4444')
    assert DriverFactory.create(config) is browser
    assert remote.call_args.kwargs['command_executor'] == config.remote_url
    assert remote.call_args.kwargs['options'].capabilities['browserName'] == 'chrome'
    browser.set_page_load_timeout.side_effect = RuntimeError('lost remote session')
    with pytest.raises(RuntimeError, match='lost remote session'):
        DriverFactory.create(config)
    browser.quit.assert_called_once()
    context = SimpleNamespace(driver=browser)
    DriverFactory.close(context)
    assert context.driver is None
