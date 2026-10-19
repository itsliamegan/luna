from pathlib import Path
import sys

from luna.cli import Command, argument, option
from luna.test.reporting import Capture, report
from luna.test.runner import Runner
from luna.test.suite import Filter, Group, Suite, Test


class LunaTest(Command):
	"""Run the test suite."""

	name = "test"
	pattern: str | None = argument(
		default=None,
		help="only run tests matching this name, if provided",
	)
	capture: Capture = option(default=Capture.ALWAYS, help="when to capture output")
	jobs: int | None = option(
		default=None,
		short="j",
		help="maximum number of tests to run in parallel",
	)

	def run(self):
		root = Path.cwd()
		# Put the project root on the import path so that test files can import
		# shared modules.
		sys.path.insert(0, str(root))
		suite = Suite.discover(Path(root, "test"))
		if self.pattern is not None:
			suite = suite.select(NameFilter(self.pattern))

		if not suite.groups:
			if self.pattern is None:
				self.fail("no tests found in test/")
			else:
				self.fail(f"no tests match {self.pattern!r}")

		results = Runner(self.jobs).run(suite)
		passed = report(results, self.capture)
		if not passed:
			raise SystemExit(1)


class NameFilter(Filter):
	def __init__(self, name: str):
		self.name = name

	def match(self, group: Group, test: Test) -> bool:
		return self.name in group.name
