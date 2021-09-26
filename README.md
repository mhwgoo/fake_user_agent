Randomly generate a fake useragent.

This project's idea is inspired by [fake-useragent](https://github.com/hellysmile/fake-useragent). I rewrote the whole codes in order to boost performance by:
  - using `asyncio` and `aiohttp` to improve fetching speed
  - taking advantage of `Xpath` to improve parsing speed
  - changing random choice algorithm to improve random choice speed

Supported browsers are: chrome, edge, firefox, safari, and opera. Browser name is case insensitive. Some other possible spellings of each browser are mapped to the right one (e.g. "ie" -> "edge", "google" -> "chrome").

# Usage
On your terminal, enter `fakeua`
![](/screenshots/browser.png)

In python script, just import the function. Every time you run your python script, the user agent is randomly chosen, so each time the value is different.
```python
from fake_user_agent.main import user_agent

# Not specify a browser:
ua = user_agent()

# Specify a browser to randomly choose from:
ua = user_agent("chrome")

# Using tempfile takes less than 0.001s from the second time. 
# Not using it takes less than 3s because of fetching data on the web each time.
# By default tempfile is used, you can turn it off by:
ua = user_agent(use_temfile=False)

# If there is an async function needing a useragent in your script, 
# don't put `user_agent()` in your async function, put it above instead. 


# You can also import multithreading version offered.
# Time taken is no big difference with the default asyncio version.
# All usages are same, except that `user_agent()` can be put within an async function. 
from fake_user_agent.thread_version import user_agent


# Remove tempfile
rm_tempfile()
```
Remove tempfile with terminal command on Linux or MacOS. Replace `var` with respective folder name on Windows
```bash
find /var/ -name "fake_useragent*" -type f -exec rm {} \;
```

# Installation
```python
pip install fake_user_agent
```

