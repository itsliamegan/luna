from collections.abc import Callable
from io import StringIO
import sys
from typing import Protocol


class Filter(Protocol):
	def match(self, test: Test, case: Case) -> bool: ...


class Result:
	def __init__(self, test_name: str, case_name: str, case_index: int):
		self.test_name = test_name
		self.case_name = case_name
		self.case_index = case_index


class Pass(Result):
	pass


class Fail(Result):
	def __init__(
		self,
		test_name: str,
		case_name: str,
		case_index: int,
		error: AssertionError,
	):
		super().__init__(test_name, case_name, case_index)
		self.error = error


class Error(Result):
	def __init__(
		self,
		test_name: str,
		case_name: str,
		case_index: int,
		error: Exception,
	):
		super().__init__(test_name, case_name, case_index)
		self.error = error


class Case:
	def __init__(self, name: str, impl: Callable[..., object]):
		self.name = name
		self.impl = impl

	def run(self, test_name: str, case_index: int) -> Result:
		stdout = sys.stdout
		stderr = sys.stderr
		sys.stdout = StringIO()
		sys.stderr = StringIO()
		try:
			self.impl()
			return Pass(test_name, self.name, case_index)
		except AssertionError as error:
			return Fail(test_name, self.name, case_index, error)
		except Exception as error:  # noqa: BLE001
			return Error(test_name, self.name, case_index, error)
		finally:
			sys.stdout = stdout
			sys.stderr = stderr

	def __repr__(self) -> str:
		return f"Case(name={self.name!r}, impl={self.impl!r})"


class Test:
	def __init__(self, name: str, cases: list[Case]):
		self.name = name
		self.cases = cases

	def run(self, filter: Filter) -> list[Result]:
		results = []
		for case_index, case in enumerate(self.cases):
			if filter.match(self, case):
				results.append(case.run(self.name, case_index))
		return results

	def __repr__(self) -> str:
		return f"Test(name={self.name!r}, cases={self.cases!r})"


class Suite:
	def __init__(self, tests: list[Test]):
		self.tests = tests

	def run(self, filter: Filter) -> list[Result]:
		results = []
		for test in self.tests:
			results += test.run(filter)
		return results

	def __repr__(self) -> str:
		return f"Suite(tests={self.tests!r})"
