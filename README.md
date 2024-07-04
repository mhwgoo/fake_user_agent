Randomly generate a valid useragent for faking a browser.

## As a binary
```bash
fakeua                     # Get a useragent without specifying a browser name
fakeua [browser]           # Get a useragent with a browser name (case insensitive)
fakeua [browser] --debug   # Get a useragent in debug mode
fakeua [browser] --nocache # Get a useragent without using local cache
fakeua --version           # Print the current version of the program
```

## As a library
```python
# Every time you run the script, the useragent value will be different.
# Supported browsers are: "chrome", "edge", "firefox", "safari", and "opera".
# No error handling is needed; the following functions return a valid useragent definitely,
# resorting to a fixed useragent if whatever error happens to avoid breaking the caller.

# For non-async caller:
from fake_user_agent import user_agent
ua = user_agent(browser=None, use_cache=True)

# For async caller:
from fake_user_agent import aio_user_agent
ua = await aio_user_agent(browser=None, use_cache=True)
```

## Install & Uninstall
```bash
pip install fake_user_agent
pip uninstall -r requirements.txt -y

# within the project
make install
make uninstall
```
