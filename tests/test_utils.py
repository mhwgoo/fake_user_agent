import pytest
import sys
import os
import json
from unittest import mock

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


from fake_useragent import utils, errors, settings
from fake_useragent.utils import urlopen_has_ssl_context


# NOTE Google blocks requests not from browser, don't test with google url
def test_utils_get():
    assert utils.get("http://info.cern.ch/") is not None

    if urlopen_has_ssl_context:
        with pytest.raises(errors.FakeUserAgentError):
            utils.get("https://expired.badssl.com/")

        assert utils.get("https://expired.badssl.com", verify_ssl=False) is not None
        assert utils.get("https://i3wm.org") is not None


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

# TODO Make test case of load() granular
def test_utils_load():
    data = utils.load(use_cache_server=True)
    x = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.77 Safari/537.36"

    assert data is not None
    assert isinstance(data["browsers"], dict)
    assert data["browsers"] is not None
    assert x in data["browsers"]["chrome"]


# TODO Make data in cache server same with data not from cache server
def test_utils_get_cache_server():
    body = utils.get(settings.CACHE_SERVER).decode("utf-8")

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
