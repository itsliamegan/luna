from collections.abc import Sequence
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path

from luna import ansi, inflect
from luna.ansi import Escape
from luna.printer import Printer
from luna.test.capture import Capture
from luna.test.group import Group
from luna.test.progress import Progress, label
from luna.test.result import Error, Fail, Pass, Result


class Reporter:
	def __init__(self, printer: Printer, progress: Progress, capture: Capture):
		self.printer = printer
		self.progress = progress
		self.capture = capture
		self.finished: list[FinishedGroup] = []

	def group_finished(self, group: Group, results: Sequence[Result]):
		self.finished.append(FinishedGroup(group, results))
		self.progress.advance(group, results)

	def suite_finished(self, elapsed: timedelta):
		self.progress.finish()

		for finished in self.finished:
			for result in finished.results:
				if self.has_details(result):
					self.printer.end_line()
					self.write_details(finished.group, result)

		self.printer.end_line()
		self.write_summary(elapsed)

	def has_details(self, result: Result) -> bool:
		match result:
			case Pass():
				written = bool(result.output.stdout or result.output.stderr)
				return written and self.capture.shows(result)
			case Fail() | Error():
				return True

	def write_details(self, group: Group, result: Result):
		self.printer.write(f"{label(result)}\t{group.name}:{result.test_name}\n")
		with self.printer.indented():
			match result:
				case Pass():
					pass
				case Fail():
					if result.location is not None:
						location = result.location
						path = location.path.relative_to(Path.cwd(), walk_up=True)
						self.printer.write(f"{path}:{location.line}\n")
						with self.printer.indented("    "):
							self.write_lines(location.source)
					self.write_lines(result.error)
				case Error():
					self.write_lines(result.error)

			if self.capture.shows(result):
				self.write_lines(result.output.stdout)
				self.write_lines(result.output.stderr)

	def write_lines(self, text: str):
		if not text:
			return

		self.printer.write(text)
		if not text.endswith("\n"):
			self.printer.end_line()

	def write_summary(self, elapsed: timedelta):
		passed = 0
		failed = 0
		errors = 0
		for finished in self.finished:
			for result in finished.results:
				match result:
					case Pass():
						passed += 1
					case Fail():
						failed += 1
					case Error():
						errors += 1

		counts = []
		if passed:
			counts.append(ansi.escape(Escape.GREEN, f"{passed} passed"))
		if failed:
			counts.append(ansi.escape(Escape.RED, f"{failed} failed"))
		if errors:
			counts.append(ansi.escape(Escape.YELLOW, inflect.count(errors, "error")))
		self.printer.write(f"{", ".join(counts)} in {elapsed.total_seconds():.2f}s\n")


@dataclass
class FinishedGroup:
	group: Group
	results: Sequence[Result]
