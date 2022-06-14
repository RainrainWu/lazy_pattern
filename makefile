# Virtual Environment
VENV_POETRY		:= poetry run
FILE_TOML		:= pyproject.toml

ifneq (,$(wildcard ./.env))
    include .env
    export
endif

.PHONY: lint
lint:
	$(VENV_POETRY) black .
	$(VENV_POETRY) isort .

.PHONY: test
test:
	$(VENV_POETRY) pytest

.PHONY: secure
secure:
	$(VENV_POETRY) safety check --bare --cache
	$(VENV_POETRY) bandit -q -r -iii -lll -c ${FILE_TOML} .
