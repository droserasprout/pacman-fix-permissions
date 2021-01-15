lint:
	poetry run black src
	poetry run flakehell lint src
	poetry run mypy src

install:
	poetry install

update:
	poetry update

build:
	poetry build
