Randomly generate a valid useragent for faking a browser behavior.

## As a binary
```bash
fakeua                     # Get a useragent without specifying a browser name
fakeua [browser]           # Get a useragent with a browser name (case insensitive)
fakeua [browser] --debug   # Get a useragent in debug mode
fakeua [browser] --nocache # Get a useragent without using local cache
fakeua --remove            # Remove cache from $HOME/.cache/fakeua
fakeua --version           # Print the current version of the program
```

## As a library
```python
# Every time you run the script, the useragent value will be different.
# Supported browsers to choose from are: "chrome", "edge", "firefox", "safari", and "opera".

# For non-async caller:
from fake_user_agent import user_agent
ua = user_agent(browser=None, use_cache=True)

# For async caller:
from fake_user_agent import aio_user_agent
ua = await aio_user_agent(browser=None, use_cache=True)

# Remove cache:
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
