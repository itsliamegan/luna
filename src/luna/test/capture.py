from abc import ABC, abstractmethod

from luna.test.result import Error, Fail, Pass, Result


class Capture(ABC):
	"""Decides which results' captured output appears in the report."""

	@abstractmethod
	def shows(self, result: Result) -> bool: ...


class AlwaysCapture(Capture):
	def shows(self, result: Result) -> bool:
		return False


class PassCapture(Capture):
	def shows(self, result: Result) -> bool:
		match result:
			case Pass():
				return False
			case Fail() | Error():
				return True


class NeverCapture(Capture):
	def shows(self, result: Result) -> bool:
		return True
