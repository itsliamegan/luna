from abc import ABC, abstractmethod

from luna.test.result import Error, Fail, Result


class Capture(ABC):
	"""Decides which results' captured output appears in the report."""

	@abstractmethod
	def shows(self, result: Result) -> bool: ...


class Always(Capture):
	def shows(self, result: Result) -> bool:
		return False


class Pass(Capture):
	def shows(self, result: Result) -> bool:
		match result:
			case Fail() | Error():
				return True
			case _:
				return False


class Never(Capture):
	def shows(self, result: Result) -> bool:
		return True
