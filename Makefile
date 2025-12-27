install:
	uv sync

update:
	uv sync -U

lint: ruff mypy

ruff:
	uv run ruff format src tests
	uv run ruff check src tests

mypy:
	uv run mypy src tests
