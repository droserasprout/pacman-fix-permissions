lint: isort black mypy

install:
	poetry install `if [ "${DEV}" = "0" ]; then echo "--no-dev"; fi`

isort:
	poetry run isort src tests

black:
	poetry run black --skip-string-normalization src tests

mypy:
	poetry run mypy src tests
