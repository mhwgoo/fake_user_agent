import pytest
import sys
import os
import json
from unittest import mock
import aiohttp


sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


from fake_useragent import aio_utils, utils, errors, settings

# NOTE Google blocks requests not from browser, don't test with google url
def test_utils_fetch():
    assert utils.fetch("https://i3wm.org") is not None
    assert utils.fetch("http://info.cern.ch/") is not None

    # This wouldn't take effect, because requests library verify certificate expired or not
    # whereas urllib doesn't verify expiration, so this line is only for urllib
    # with pytest.raises(errors.FakeUserAgentError):
    #    utils.get("https://expired.badssl.com/")


@pytest.mark.asyncio
async def test_aio_utils_fetch():
    async with aiohttp.ClientSession() as session:
        assert aio_utils.fetch("https://i3wm.org", session) is not None
        assert aio_utils.fetch("http://info.cern.ch/", session) is not None
        with pytest.raises(errors.FakeUserAgentError):
            aio_utils.fetch(settings.BROWSERS_STATS_PAGE, session)


@pytest.mark.asyncio
async def test_aio_utils_load():
    assert aio_utils.load() is not None


# After get rid of get_browsers(), this way of test doesn't needed
# @mock.patch("fake_useragent.utils.get_browsers")
# def test_utils_load(mock_get_browsers):
#    # NOTE:side_effect should have same arguments with target function
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
#    data = utils.load()
#    x = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.77 Safari/537.36"
#
#    assert data is not None
#    assert isinstance(data["browsers"], dict)
#    assert data["randomize"] is not None
#    assert x in data["browsers"]["chrome"]


def test_utils_load():
    data = utils.load()
    x = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.77 Safari/537.36"

    assert data is not None
    assert isinstance(data["browsers"], dict)
    assert data["browsers"] is not None
    assert x in data["browsers"]["chrome"]


def test_utils_get_cache_server():
    body = utils.fetch(settings.CACHE_SERVER)

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
