Randomly generate a fake useragent. Supported browsers are: chrome, edge, firefox, safari, and opera.

## As a binary
```bash
fakeua                     # Get a useragent without a browser name
fakeua [browser]           # Get a useragent with a browser name (case insensitive)
fakeua [browser] --debug   # Get a useragent in debug mode
fakeua [browser] --nocache # Get a useragent without using local cache
fakeua --remove            # Remove cache from $HOME/.cache/fakeua folder
fakeua --version           # Print the current version of the program
```
## As a library
```python
from fake_user_agent import user_agent

# Every time you run the script, the useragent value will be different.
# Not to specify a browser
ua = user_agent()

# Or specify a browser to randomly choose from
ua = user_agent(browser="chrome")

# `use_cache=True` by default.
# It takes less than 2s for the first run, including fetching, parsing, and writing cache. 
# It takes less than 0.01s starting from the second time by using cache.
# `use_cache=False` not to use cache.
ua = user_agent(use_cache=False)

# If there is an async function needing a useragent in your script,
# don't put `user_agent()` in your async function, put it above instead.

# Remove cache.
from fake_user_agent import rm_cache
rm_cache()  
```

## Install & Uninstall
```bash
pip install fake_user_agent
pip uninstall -r requirements.txt -y
rm -rf $HOME/.cache/fakeua

# within the project
make install
make uninstall
make clean_cache
```
