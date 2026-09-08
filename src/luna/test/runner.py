from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys
from types import ModuleType

from luna.cli import Argument, Option, Program
from luna.test import Case, Filter, Suite, Test
from luna.test.reporting import Capture, report


class EmptyFilter(Filter):
	def match(self, test: Test, case: Case) -> bool:
		return True


class TestNameFilter(Filter):
	def __init__(self, name: str):
		self.name = name

	def match(self, test: Test, case: Case) -> bool:
		return self.name in test.name


def import_from_file(path: Path, module_name: str) -> ModuleType:
	spec = spec_from_file_location(module_name, path)
	if spec is None or spec.loader is None:
		raise ImportError(f"Cannot load test module from {path}")

	module = module_from_spec(spec)
	spec.loader.exec_module(module)
	return module


def run(pattern: str, capture: Capture):
	if pattern == "*":
		filter = EmptyFilter()
	else:
		filter = TestNameFilter(pattern)

	test_dir = Path.cwd().joinpath("test")
	tests = []
	for dir, dirs, files in test_dir.walk():
		for file in files:
			path = dir.joinpath(file)
			if path.suffix == ".py" and path.stem.endswith("_test"):
				relative_path = path.relative_to(test_dir).with_suffix("")
				module_name = ".".join(relative_path.parts)
				module = import_from_file(path, module_name)
				cases = []
				test = Test(relative_path.as_posix(), cases)
				for name, item in module.__dict__.items():
					if name.startswith("test") and callable(item):
						case = Case(name, item)
						cases.append(case)
				tests.append(test)
	suite = Suite(tests)
	results = suite.run(filter)

	passed = report(results, capture)
	if not passed:
		raise SystemExit(1)


def main():
	program = Program(
		"luna test",
		run,
		arguments=[
			Argument(
				"pattern",
				required=False,
				default="*",
				help="only run tests matching this name, if provided",
			)
		],
		options=[
			Option(
				"capture",
				type=Capture,
				default=Capture.ALWAYS,
				help="when to capture output (always, pass, never)",
			)
		],
	)
	program.run(sys.argv)


if __name__ == "__main__":
	main()
