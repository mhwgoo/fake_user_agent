Randomly generate a fake useragent.

This project's idea is inspired by [fake-useragent](https://github.com/hellysmile/fake-useragent). I rewrote the whole codes in order to boost performance by:
  - using `asyncio` and `aiohttp` to improve fetching speed
  - taking advantage of `Xpath` to improve parsing speed
  - changing random choice algorithm to improve random choice speed

Supported browsers are: chrome, edge, firefox, safari, and opera. Browser name is case insensitive. Some other possible spellings of each browser are mapped to the right one (e.g. "ie" -> "edge", "google" -> "chrome").

# Usage
On your terminal, enter `fakeua`
![](/screenshots/new.png)

In python script, just import the function. Every time you run your python script, the user agent value is different.
```python
from fake_user_agent.main import user_agent

# Not specify a browser:
ua = user_agent()

# Specify a browser to randomly choose from:
ua = user_agent("chrome")

# It usually takes < 2s for the first run, including the time for fetching and parsing. 
# Using tempfile, it takes < 0.01s from the second time.
# By default, tempfile is used, it can be turned off and it will take < 2s to run:
ua = user_agent(use_tempfile=False)

# If there is an async function needing a useragent in your script,
# don't put `user_agent()` in your async function, put it above instead.

# Remove tempfile in python script. 
# May need sudo python yourscript.py for Linux
from fake_user_agent.main import rm_tempfile
rm_tempfile()  
```

Remove tempfile on Linux or MacOS terminal. Replace `var` with respective folder name on Windows
```bash
find /var/ -name "fake_useragent*" -type f -exec rm {} \; # For MacOS
find /tmp/ -name "fake_useragent*" -type f -exec rm {} \; # For Linux
```

# Installation
```python
pip install fake_user_agent
```
