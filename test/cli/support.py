from collections.abc import Generator
from contextlib import contextmanager
import os


@contextmanager
def terminal_width(columns: int) -> Generator[None]:
	previous = os.environ.get("COLUMNS")
	os.environ["COLUMNS"] = str(columns)
	try:
		yield
	finally:
		if previous is None:
			del os.environ["COLUMNS"]
		else:
			os.environ["COLUMNS"] = previous
