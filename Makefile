install:
	python3 -m pip install -r requirements.txt
uninstall:
	python3 -m pip uninstall -r requirements.txt -y

gen:
	python3 -m pip freeze > requirements.txt

check:
	@echo "\n===> running Python linter - ruff"
	ruff check
	@echo "\n===> running static type checker - pyright"
	pyright
	@echo ""

env:
	python3 -m venv venv
clean_env:
	@rm -rf venv

release:
	find fake_useragent.json || python3 user_agent.py -d -l fake_useragent.json && flit publish
	@echo "\n===> waiting 3 seconds for PYPI being able to give the newest version"
	@sleep 3
	python3 -m pip install fake_user_agent --upgrade
	python3 -m pip freeze > requirements.txt

.PHONY: clean
clean:
	@rm -rf .DS_Store
	@rm -rf .ruff_cache/
	@rm -rf dist/
	@rm -rf __pycache__/
