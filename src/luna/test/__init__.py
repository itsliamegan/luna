from pathlib import Path
from typing import Protocol


class Output:
	def __init__(self, stdout: str, stderr: str):
		self.stdout = stdout
		self.stderr = stderr


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
		error: str,
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
		error: str,
		output: Output,
	):
		super().__init__(test_name, case_name, case_index, output)
		self.error = error


class Case:
	def __init__(self, name: str):
		self.name = name

	def __repr__(self) -> str:
		return f"Case(name={self.name!r})"


class Test:
	def __init__(self, name: str, path: Path, cases: list[Case]):
		self.name = name
		self.path = path
		self.cases = cases

	def __repr__(self) -> str:
		return f"Test(name={self.name!r}, path={self.path!r}, cases={self.cases!r})"


class Suite:
	def __init__(self, tests: list[Test]):
		self.tests = tests

	def __repr__(self) -> str:
		return f"Suite(tests={self.tests!r})"


class Filter(Protocol):
	def match(self, test: Test, case: Case) -> bool: ...
