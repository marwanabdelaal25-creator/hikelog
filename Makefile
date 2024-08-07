.PHONY: test cov lint install clean

install:
	pip install -e ".[dev]"

test:
	pytest -q

cov:
	pytest --cov=hikelog --cov-report=term-missing -q

lint:
	ruff check src tests

clean:
	rm -rf build dist .pytest_cache htmlcov .coverage *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
