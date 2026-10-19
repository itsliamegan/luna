from abc import ABC, abstractmethod
from collections.abc import Sequence

from luna import ansi
from luna.printer import Printer
from luna.test.group import Group
from luna.test.result import Result


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
			label = ansi.escape(result.status.color, result.status.label)
			self.printer.write(f"{label}\t{group.name}:{result.test.name}\n")

	def finish(self):
		pass
