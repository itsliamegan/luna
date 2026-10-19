from abc import ABC, abstractmethod
from collections.abc import Sequence

from luna import ansi
from luna.ansi import Escape
from luna.printer import Printer
from luna.test.group import Group
from luna.test.result import Error, Fail, Pass, Result


class Progress(ABC):
	@abstractmethod
	def advance(self, group: Group, results: Sequence[Result]): ...

	@abstractmethod
	def finish(self): ...


class Dots(Progress):
	def __init__(self, printer: Printer):
		self.printer = printer

	def advance(self, group: Group, results: Sequence[Result]):
		for result in results:
			match result:
				case Pass():
					indicator = ansi.escape(Escape.GREEN, ".")
				case Fail():
					indicator = ansi.escape(Escape.RED, "F")
				case Error():
					indicator = ansi.escape(Escape.YELLOW, "E")
			self.printer.write(indicator)

	def finish(self):
		self.printer.end_line()


class Lines(Progress):
	def __init__(self, printer: Printer):
		self.printer = printer

	def advance(self, group: Group, results: Sequence[Result]):
		for result in results:
			match result:
				case Pass():
					label = ansi.escape(Escape.GREEN, "PASS")
				case Fail():
					label = ansi.escape(Escape.RED, "FAIL")
				case Error():
					label = ansi.escape(Escape.YELLOW, "ERROR")
			self.printer.write(f"{label}\t{group.name}:{result.test.name}\n")

	def finish(self):
		pass
