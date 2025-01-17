black = black tsflex tests
isort = isort tsflex tests

.PHONY: format
format:
	$(isort)
	$(black)

.PHONY: lint
lint:
	poetry run ruff tsflex tests
	poetry run $(isort) --check-only --df
	poetry run $(black) --check --diff

.PHONY: test
test:
	poetry run pytest --cov-report term-missing --cov=tsflex tests

.PHONY: clean
clean:
	rm -rf `find . -name __pycache__`
	rm -rf .cache
	rm -rf .pytest_cache
	rm -rf *.egg-info
	rm -rf .ruff_cache
	rm -f .coverage
