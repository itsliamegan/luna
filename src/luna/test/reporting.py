import traceback

from luna import ansi
from luna.ansi import Escape
from luna.test import Error, Fail, Pass, Result


def report(results: list[Result]) -> bool:
	def sort_key(result: Result) -> tuple[str, int]:
		return result.test_name, result.case_index

	passed = True
	for result in sorted(results, key=sort_key):
		if isinstance(result, Pass):
			desc = ansi.escape(Escape.GREEN, "PASS")
		elif isinstance(result, Fail):
			desc = ansi.escape(Escape.RED, "FAIL")
			passed = False
		elif isinstance(result, Error):
			desc = ansi.escape(Escape.YELLOW, "ERROR")
			passed = False

		print(f"{desc}\t{result.test_name}:{result.case_name}")

		if isinstance(result, (Fail, Error)):
			if isinstance(result, Fail) and str(result.error):
				for line in str(result.error).splitlines():
					print(f"\t{line}")
			elif isinstance(result, Error):
				traceback_start = result.error.__traceback__
				if traceback_start is not None:
					# Skip the internal test case call so the traceback points
					# at where the error was actually raised.
					traceback_start = traceback_start.tb_next
				formatted = traceback.format_exception(
					type(result.error), result.error, traceback_start
				)
				for line in "".join(formatted).splitlines():
					print(f"\t{line}")

	return passed
