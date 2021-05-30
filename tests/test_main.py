import pytest
import sys
import os
from unittest import mock
from requests import exceptions
import aiohttp

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


from fake_useragent import aio_main, main, errors, settings


def test_main_fetch():
    assert main.fetch("https://i3wm.org") is not None
    assert main.fetch("http://info.cern.ch/") is not None

    # with pytest.raises(exceptions.SSLError):
    #    main.fetch("https://expired.badssl.com/")

    with pytest.raises(errors.FakeUserAgentError):
        main.fetch(settings.BROWSERS_STATS_PAGE)


def test_main_load():
    main.load()
    data = main.all_versions
    x = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.77 Safari/537.36"
    assert data is not None
    assert isinstance(data["chrome"], list)
    assert x in data["chrome"]


@pytest.mark.asyncio
async def test_aio_main_fetch():
    async with aiohttp.ClientSession() as session:
        result1 = await aio_main.fetch("https://i3wm.org", session)
        assert result1 is not None

        result2 = await aio_main.fetch("http://info.cern.ch/", session)
        assert result2 is not None

        with pytest.raises(errors.FakeUserAgentError):
            await aio_main.fetch(settings.BROWSERS_STATS_PAGE, session)
