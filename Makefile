install:
	python3 -m pip install -r requirements.txt
uninstall:
	python3 -m pip uninstall -r requirements.txt -y
clean_cache:
	@rm -rf $HOME/.cache/fakeua

gen:
	python3 -m pip freeze > requirements.txt

check:
	@echo "\n===> running Python linter - ruff"
	ruff check fake_user_agent
	@echo "\n===> running static type checker - pyright"
	pyright fake_user_agent
	@echo ""

env:
	python3 -m venv venv
clean_env:
	@rm -rf venv 

release:
	flit publish
	python3 -m pip install fake_user_agent --upgrade
	python3 -m pip freeze > requirements.txt

.PHONY: clean
clean:
	@rm -rf fake_user_agent/__pycache__
	@rm -rf fake_user_agent/.DS_Store
	@rm -rf fake_user_agent/.ruff_cache
	@rm -rf .DS_Store
	@rm -rf .ruff_cache/
	@rm -rf dist/
