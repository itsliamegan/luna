from datetime import timedelta
from enum import StrEnum
from pathlib import Path
import sys
import time

from luna.cli import Command, argument, option
from luna.printer import Printer
from luna.test import capture, filter, progress
from luna.test.reporter import Reporter
from luna.test.result import Error, Fail, Pass
from luna.test.runner import Runner
from luna.test.suite import Suite


class ProgressStyle(StrEnum):
	DOTS = "dots"
	LINES = "lines"


class CaptureStyle(StrEnum):
	ALWAYS = "always"
	PASS = "pass"
	NEVER = "never"


class LunaTest(Command):
	"""Run the test suite."""

	name = "test"
	pattern: str | None = argument(
		default=None,
		help="only run tests matching this name, if provided",
	)
	progress: ProgressStyle = option(
		default=ProgressStyle.DOTS,
		help="how to show progress",
	)
	capture: CaptureStyle = option(
		default=CaptureStyle.ALWAYS,
		help="when to capture output",
	)
	jobs: int | None = option(
		default=None,
		short="j",
		help="maximum number of tests to run in parallel",
	)

	def run(self):
		started = time.perf_counter()
		root = Path.cwd()
		# Put the project root on the import path so that test files can import
		# shared modules.
		sys.path.insert(0, str(root))
		suite = Suite.discover(Path(root, "test"))
		if self.pattern is not None:
			suite = suite.select(filter.Name(self.pattern))

		if not suite.groups:
			if self.pattern is None:
				self.fail("no tests found in test/")
			else:
				self.fail(f"no tests match {self.pattern!r}")

		printer = Printer(sys.stdout)
		match self.progress:
			case ProgressStyle.DOTS:
				progress_ = progress.Dots(printer)
			case ProgressStyle.LINES:
				progress_ = progress.Lines(printer)

		match self.capture:
			case CaptureStyle.ALWAYS:
				capture_ = capture.Always()
			case CaptureStyle.PASS:
				capture_ = capture.OnlyPass()
			case CaptureStyle.NEVER:
				capture_ = capture.Never()

		reporter = Reporter(printer, progress_, capture_)
		results = Runner(self.jobs).run(suite, reporter)
		reporter.suite_finished(timedelta(seconds=time.perf_counter() - started))

		for result in results:
			match result:
				case Pass():
					pass
				case Fail() | Error():
					raise SystemExit(1)
