from abc import ABC, abstractmethod

from luna.test.result import Error, Fail, Pass, Result


class Capture(ABC):
	"""Decides which results' captured output appears in the report."""

	@abstractmethod
	def shows(self, result: Result) -> bool: ...


class Always(Capture):
	def shows(self, result: Result) -> bool:
		return False


class OnlyPass(Capture):
	def shows(self, result: Result) -> bool:
		match result:
			case Pass():
				return False
			case Fail() | Error():
				return True


class Never(Capture):
	def shows(self, result: Result) -> bool:
		return True
