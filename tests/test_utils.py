import pytest
import sys
import os
import json
from unittest import mock
import aiohttp


sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


from fake_useragent import aio_main, main, errors, settings


def test_main_fetch():
    assert main.fetch("https://i3wm.org") is not None
    assert main.fetch("http://info.cern.ch/") is not None

    # This wouldn't take effect, because requests library verify certificate expired or not
    # whereas urllib doesn't verify expiration, so this line is only for urllib
    # with pytest.raises(errors.FakeUserAgentError):
    #    main.fetch("https://expired.badssl.com/")


@pytest.mark.asyncio
async def test_aio_main_fetch():
    async with aiohttp.ClientSession() as session:
        assert aio_main.fetch("https://i3wm.org", session) is not None
        assert aio_main.fetch("http://info.cern.ch/", session) is not None
        with pytest.raises(errors.FakeUserAgentError):
            aio_main.fetch(settings.BROWSERS_STATS_PAGE, session)


# After removing get_browsers(), this test doesn't needed
# @mock.patch("fake_useragent.main.get_browsers")
# def test_main_load(mock_get_browsers):
#    # side_effect should have same arguments with target function
#    # becaue it replaces target function in test execution
#    def side_effect(verify_ssl=True):
#        return [
#            ("Chrome", " 90"),
#            ("Edge", " 4"),
#            ("Firefox", " 3"),
#            ("Safari", " 2"),
#            ("Opera", " 1"),
#        ]
#
#    mock_get_browsers.side_effect = side_effect
#    data = main.load()
#    x = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.77 Safari/537.36"
#
#    assert data is not None
#    assert isinstance(data["browsers"], dict)
#    assert data["randomize"] is not None
#    assert x in data["browsers"]["chrome"]


def test_main_load():
    data = main.load()
    x = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.77 Safari/537.36"
    assert data is not None
    assert isinstance(data["browsers"], dict)
    assert data["browsers"] is not None
    assert x in data["browsers"]["chrome"]


def test_main_get_cache_server():
    body = main.fetch(settings.CACHE_SERVER)
    data = json.loads(body)
    expected = {
        "randomize": mock.ANY,
        "browsers": {
            "chrome": mock.ANY,
            "firefox": mock.ANY,
            "opera": mock.ANY,
            "safari": mock.ANY,
            "internetexplorer": mock.ANY,
        },
    }
    assert expected == data
