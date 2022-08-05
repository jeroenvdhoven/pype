

install:
	pip install -e .

test:
	python -m pytest

coverage:
	python -m pytest --cov-report term-missing --cov pype -ra

# Pre-commit defaults
pre-commit-install:
	pip install pre-commit
	pre-commit install --hook-type pre-commit --hook-type pre-push --hook-type commit-msg

pre-commit-run:
	pre-commit run --all-files
