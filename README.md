Randomly generate a fake useragent.

This project's idea is inspired by [fake-useragent](https://github.com/hellysmile/fake-useragent/tree/master/fake_useragent). I rewrote the whole codes in order to boost performance by:
  - using asyncio and aiohttp to improve fetching speed
  - taking advantage of Xpath to improve parsing speed
  - changing random choice algorithm to improve random choice speed

# Usage
On terminal, enter `fakeua`
![](/screenshots/browser.png)

In python script, import function

```python
from fake_user_agent.main import user_agent

# Not specify a browser:
ua = user_agent()    

# Specify a browser to random from:
ua = user_agent("chrome")
```
# Installation
```python
pip install fake_user_agent
```

