from abc import ABC, abstractmethod

from luna.test.result import Result


class Capture(ABC):
	"""Decides which results' captured output appears in the report."""

	@abstractmethod
	def shows(self, result: Result) -> bool: ...


class Always(Capture):
	def shows(self, result: Result) -> bool:
		return False


class OnlyPass(Capture):
	def shows(self, result: Result) -> bool:
		return result.status.failing


class Never(Capture):
	def shows(self, result: Result) -> bool:
		return True
