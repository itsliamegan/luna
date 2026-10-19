from collections.abc import Generator
from contextlib import contextmanager
from typing import TextIO


class Printer:
	"""Writes text to a stream, indenting lines that start while indented.

	Empty lines are left unindented.
	"""

	def __init__(self, stream: TextIO):
		self.stream = stream
		self.prefixes: list[str] = []
		self.at_line_start = True

	def write(self, text: str):
		for line in text.splitlines(keepends=True):
			if self.at_line_start and line != "\n":
				self.stream.write("".join(self.prefixes))
			self.stream.write(line)
			self.at_line_start = line.endswith("\n")

	def end_line(self):
		self.stream.write("\n")
		self.at_line_start = True

	@contextmanager
	def indented(self, prefix: str = "\t") -> Generator[None]:
		self.prefixes.append(prefix)
		try:
			yield
		finally:
			self.prefixes.pop()
