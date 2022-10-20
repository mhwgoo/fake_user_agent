Randomly generate a fake useragent.

This project's idea is inspired by [fake-useragent](https://github.com/hellysmile/fake-useragent). I rewrote the whole codes in order to boost performance by:
  - using `asyncio` and `aiohttp` to improve fetching speed
  - taking advantage of `Xpath` to improve parsing speed
  - changing random choice algorithm to improve random choice speed

Supported browsers are: chrome, edge, firefox, safari, and opera. Browser name is case insensitive. Some other possible spellings of each browser are mapped to the right one (e.g. "ie" -> "edge", "google" -> "chrome").

It takes less than 2s for the first run, including fetching, parsing, and writing cache. 

It will take less than 0.01s starting from the second time by using cache by default. 

# Usage
### As a binary
On your terminal, just simply enter `fakeua`
![](/screenshots/new.png)

Other usages on terminal:
```bash
# Get a useragent in debug mode
fakeua <browser or omit> --debug

# Get a useragent without local caching
fakeua <browser or omit> --nocache

# Remove cache from $HOME/.cache/fakeua folder
fakeua --remove  

# Print the current version of the program
fakeua --version
```

### As a library
In your python script, import the function. Every time you run the script, the useragent value will be different.
```python
from fake_user_agent import user_agent

# Not to specify a browser
ua = user_agent()

# Specify a browser to randomly choose from
ua = user_agent("chrome")

# Specify not using cache, it will take < 1s to run, including fetching and parsing.
ua = user_agent(use_cache=False)

# If there is an async function needing a useragent in your script,
# don't put `user_agent()` in your async function, put it above instead.

# Remove cache in a python script. 
# May need `sudo python yourscript.py` for Linux.
from fake_user_agent import rm_cache
rm_cache()  
```

# Installation
```python
pip install fake_user_agent
```
