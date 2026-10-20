test:
	uv run luna test

lint:
	uv run ruff format
	uv run ruff check --fix

check:
	uv run ty check
