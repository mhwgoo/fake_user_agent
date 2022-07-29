Randomly generate a fake useragent.

This project's idea is inspired by [fake-useragent](https://github.com/hellysmile/fake-useragent). I rewrote the whole codes in order to boost performance by:
  - using `asyncio` and `aiohttp` to improve fetching speed
  - taking advantage of `Xpath` to improve parsing speed
  - changing random choice algorithm to improve random choice speed

Supported browsers are: chrome, edge, firefox, safari, and opera. Browser name is case insensitive. Some other possible spellings of each browser are mapped to the right one (e.g. "ie" -> "edge", "google" -> "chrome").

# Usage
On your terminal, just simply enter `fakeua`
![](/screenshots/new.png)

In your python script, import the function. Every time you run the script, the useragent value will be different.
```python
from fake_user_agent import user_agent

# Not specify a browser:
ua = user_agent()

# Specify a browser to randomly choose from:
ua = user_agent("chrome")

# It takes < 2s for the first run based on my 200M bandwith, including fetching, parsing, and writing cache. 
# Using tempfile by default, it takes < 0.01s starting from the second time. 
# You can specify not using tempfile, and it will take < 1s to run, including fetching and parsing:
ua = user_agent(use_tempfile=False)

# If there is an async function needing a useragent in your script,
# don't put `user_agent()` in your async function, put it above instead.

# Remove tempfile in a python script. 
# May need `sudo python yourscript.py` for Linux.
from fake_user_agent import rm_tempfile
rm_tempfile()  
```

Other usages on terminal
```bash
# Set to get a useragent in debug mode
fakeua <browser or omit> --debug

# Set to get a useragent without local caching
fakeua <browser or omit> --nocache

# Remove cache from tempfile folder
fakeua --remove  

# Print the current version of the program
fakeua --version
```

# Installation
```python
pip install fake_user_agent
```
