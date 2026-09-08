from collections.abc import Callable
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import dataclass
from io import StringIO
from typing import Protocol


class Filter(Protocol):
	def match(self, test: Test, case: Case) -> bool: ...


@dataclass(frozen=True)
class Output:
	stdout: str
	stderr: str


class Result:
	def __init__(
		self,
		test_name: str,
		case_name: str,
		case_index: int,
		output: Output,
	):
		self.test_name = test_name
		self.case_name = case_name
		self.case_index = case_index
		self.output = output


class Pass(Result):
	pass


class Fail(Result):
	def __init__(
		self,
		test_name: str,
		case_name: str,
		case_index: int,
		error: AssertionError,
		output: Output,
	):
		super().__init__(test_name, case_name, case_index, output)
		self.error = error


class Error(Result):
	def __init__(
		self,
		test_name: str,
		case_name: str,
		case_index: int,
		error: Exception,
		output: Output,
	):
		super().__init__(test_name, case_name, case_index, output)
		self.error = error


class Case:
	def __init__(self, name: str, impl: Callable[..., object]):
		self.name = name
		self.impl = impl

	def run(self, test_name: str, case_index: int) -> Result:
		stdout = StringIO()
		stderr = StringIO()
		with redirect_stdout(stdout), redirect_stderr(stderr):
			try:
				self.impl()
				error = None
			except AssertionError as caught:
				error = caught
			except Exception as caught:  # noqa: BLE001
				error = caught

		output = Output(stdout.getvalue(), stderr.getvalue())
		if error is None:
			return Pass(test_name, self.name, case_index, output)
		elif isinstance(error, AssertionError):
			return Fail(test_name, self.name, case_index, error, output)
		else:
			return Error(test_name, self.name, case_index, error, output)

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
