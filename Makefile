.PHONY: prepare update install isort black pylint mypy test build publish clean lint all ci
.DEFAULT_GOAL := all

lint: isort black pylint mypy
all: install lint test build
ci: all

# NOTE: MacOS default, set to `python` in Linux environments
PYTHON = `pyenv which python`
POETRY_VERSION = 1.1.4
POETRY = ${PYTHON} ${HOME}/.poetry/bin/poetry

PROJECT = pacman-fix-permissions
PACKAGE = pacman_fix_permissions
DEV ?= 1

prepare:
	curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/get-poetry.py | POETRY_VERSION=${POETRY_VERSION} ${PYTHON} -

update:
	${POETRY} update -vvv

install:
	make prepare
	${POETRY} install -vvv --remove-untracked `if [ "${DEV}" = "0" ]; then echo "--no-dev"; fi`

isort:
	${POETRY} run isort --recursive src tests

black:
	${POETRY} run black --skip-string-normalization src tests

pylint:
	${POETRY} run pylint src tests || ${POETRY} run pylint-exit $$?

mypy:
	${POETRY} run mypy src tests


test:
	# ${POETRY} run nosetests -v --with-timer --with-coverage tests --cover-package $(PACKAGE)

build:
	${POETRY} build

publish:
	${POETRY} publish --build

clean:
	rm -rf build dist .venv poetry.lock .mypy_cache
