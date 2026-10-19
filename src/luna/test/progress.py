from abc import ABC, abstractmethod
from collections.abc import Sequence

from luna import ansi
from luna.ansi import Escape
from luna.printer import Printer
from luna.test import Error, Fail, Pass, Result
from luna.test.group import Group


class Progress(ABC):
	@abstractmethod
	def advance(self, group: Group, results: Sequence[Result]): ...

	@abstractmethod
	def finish(self): ...


class Lines(Progress):
	def __init__(self, printer: Printer):
		self.printer = printer

	def advance(self, group: Group, results: Sequence[Result]):
		for result in results:
			self.printer.write(f"{label(result)}\t{group.name}:{result.test_name}\n")

	def finish(self):
		pass


def label(result: Result) -> str:
	if isinstance(result, Pass):
		return ansi.escape(Escape.GREEN, "PASS")
	elif isinstance(result, Fail):
		return ansi.escape(Escape.RED, "FAIL")
	elif isinstance(result, Error):
		return ansi.escape(Escape.YELLOW, "ERROR")
	else:
		raise TypeError(f"unknown result: {result!r}")
