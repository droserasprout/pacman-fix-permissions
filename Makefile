lint: isort black mypy

install:
	poetry install `if [ "${DEV}" = "0" ]; then echo "--no-dev"; fi`

isort:
	isort src tests

black:
	black --skip-string-normalization src tests

mypy:
	mypy src tests
