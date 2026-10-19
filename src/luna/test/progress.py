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
