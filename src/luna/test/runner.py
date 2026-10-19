from concurrent.futures import ProcessPoolExecutor
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import dataclass
from io import StringIO
import traceback
from types import ModuleType

from luna.test import Error, Fail, Location, Output, Pass, Result
from luna.test.group import Group
from luna.test.reporter import Reporter
from luna.test.suite import Suite
from luna.test.test import Test


@dataclass
class Runner:
	jobs: int | None = None

	def run(self, suite: Suite, reporter: Reporter) -> list[Result]:
		results = []
		with ProcessPoolExecutor(max_workers=self.jobs) as executor:
			# Results arrive in submission order, so groups that finish early wait
			# for the groups before them.
			finished = executor.map(run_group, suite.groups)
			for group, group_results in zip(suite.groups, finished, strict=True):
				reporter.group_finished(group, group_results)
				results.extend(group_results)
		return results


def run_group(group: Group) -> list[Result]:
	module = group.import_module()
	return [run_test(group, module, test) for test in group.tests]


def run_test(group: Group, module: ModuleType, test: Test) -> Result:
	stdout = StringIO()
	stderr = StringIO()
	with redirect_stdout(stdout), redirect_stderr(stderr):
		try:
			impl = getattr(module, test.name)
			impl()
			error = None
		except AssertionError as caught:
			error = caught
		except Exception as caught:
			error = caught

	output = Output(stdout.getvalue(), stderr.getvalue())
	if error is None:
		return Pass(group.name, test.name, output)
	if isinstance(error, AssertionError):
		return Fail(
			group.name,
			test.name,
			str(error),
			output,
			location=Location.from_traceback(error.__traceback__, group.path),
		)

	traceback_start = error.__traceback__
	if traceback_start is not None:
		traceback_start = traceback_start.tb_next
	formatted = traceback.format_exception(type(error), error, traceback_start)
	return Error(group.name, test.name, "".join(formatted), output)
