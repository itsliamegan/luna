from collections.abc import Sequence
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path

from luna import ansi, inflect
from luna.printer import Printer
from luna.test.capture import Capture
from luna.test.group import Group
from luna.test.progress import Progress
from luna.test.result import Error, Fail, Pass, Result, Status


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
		if result.status.failing:
			return True
		else:
			return bool(result.output) and self.capture.shows(result)

	def write_details(self, group: Group, result: Result):
		label = ansi.escape(result.status.color, result.status.label)
		self.printer.write(f"{label}\t{group.name}:{result.test.name}\n")
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
					self.write_lines(result.message)
				case Error():
					self.write_lines(result.traceback)

			if self.capture.shows(result):
				self.write_lines(result.output)

	def write_lines(self, text: str):
		if not text:
			return

		self.printer.write(text)
		if not text.endswith("\n"):
			self.printer.end_line()

	def write_summary(self, elapsed: timedelta):
		counts = []
		for status in Status:
			count = 0
			for finished in self.finished:
				for result in finished.results:
					if result.status is status:
						count += 1
			if not count:
				continue

			match status:
				case Status.PASS:
					text = f"{count} passed"
				case Status.FAIL:
					text = f"{count} failed"
				case Status.ERROR:
					text = inflect.count(count, "error")
			counts.append(ansi.escape(status.color, text))
		self.printer.write(f"{", ".join(counts)} in {elapsed.total_seconds():.2f}s\n")


@dataclass
class FinishedGroup:
	group: Group
	results: Sequence[Result]
