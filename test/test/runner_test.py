from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory

from luna.printer import Printer
from luna.test import capture
from luna.test.assertion import (
	assert_eq,
	assert_in,
	assert_is_instance,
	assert_not_eq,
	assert_not_in,
	assert_not_none,
	assert_that,
)
from luna.test.progress import Lines
from luna.test.reporter import Reporter
from luna.test.result import Error, Fail, Pass
from luna.test.runner import Runner
from luna.test.suite import Suite


def test_runs_test_files_in_parallel():
	with TemporaryDirectory() as temporary_dir:
		test_dir = Path(temporary_dir).joinpath("test")
		test_dir.mkdir()
		first_pid = Path(temporary_dir).joinpath("first.pid")
		second_pid = Path(temporary_dir).joinpath("second.pid")
		for name, own_pid, other_pid in [
			("first", first_pid, second_pid),
			("second", second_pid, first_pid),
		]:
			test_dir.joinpath(f"{name}_test.py").write_text(
				"from pathlib import Path\n"
				"import os\n"
				"import time\n\n"
				"def test_case():\n"
				f"\tPath({str(own_pid)!r}).write_text(str(os.getpid()))\n"
				"\tdeadline = time.monotonic() + 5\n"
				f"\tother = Path({str(other_pid)!r})\n"
				"\twhile not other.exists() and time.monotonic() < deadline:\n"
				"\t\ttime.sleep(0.01)\n"
				"\tassert other.exists()\n"
			)

		printer = Printer(StringIO())
		reporter = Reporter(printer, Lines(printer), capture.Always())
		results = Runner(jobs=2).run(Suite.discover(test_dir), reporter)

		assert_that(all(isinstance(result, Pass) for result in results))
		assert_not_eq(first_pid.read_text(), second_pid.read_text())


def test_reports_groups_in_discovery_order():
	with TemporaryDirectory() as temporary_directory:
		test_directory = Path(temporary_directory, "test")
		test_directory.mkdir()
		Path(test_directory, "order_test.py").write_text(
			"import time\n\ndef test_place():\n\ttime.sleep(0.5)\n"
		)
		Path(test_directory, "user_test.py").write_text("def test_create():\n\tpass\n")
		stream = StringIO()
		printer = Printer(stream)
		reporter = Reporter(printer, Lines(printer), capture.Always())

		Runner(jobs=2).run(Suite.discover(test_directory), reporter)

	lines = stream.getvalue().splitlines()
	assert_in("order_test:test_place", lines[0])
	assert_in("user_test:test_create", lines[1])


def test_imports_each_test_file_once_during_execution():
	with TemporaryDirectory() as temporary_dir:
		test_dir = Path(temporary_dir).joinpath("test")
		test_dir.mkdir()
		imports = Path(temporary_dir).joinpath("imports")
		test_dir.joinpath("example_test.py").write_text(
			"from pathlib import Path\n\n"
			f"imports = Path({str(imports)!r})\n"
			"count = int(imports.read_text()) if imports.exists() else 0\n"
			"imports.write_text(str(count + 1))\n\n"
			"def test_first():\n"
			"\tpass\n\n"
			"def test_second():\n"
			"\tpass\n"
		)

		suite = Suite.discover(test_dir)
		printer = Printer(StringIO())
		reporter = Reporter(printer, Lines(printer), capture.Always())
		results = Runner(jobs=1).run(suite, reporter)

		assert_that(all(isinstance(result, Pass) for result in results))
		assert_eq(imports.read_text(), "2")


def test_formats_error_tracebacks_without_runner_frames():
	with TemporaryDirectory() as temporary_dir:
		test_dir = Path(temporary_dir).joinpath("test")
		test_dir.mkdir()
		test_dir.joinpath("error_test.py").write_text(
			'def test_error():\n\traise ValueError("unexpected")\n'
		)

		printer = Printer(StringIO())
		reporter = Reporter(printer, Lines(printer), capture.Always())
		results = Runner(jobs=1).run(Suite.discover(test_dir), reporter)

	result = results[0]
	error = assert_is_instance(result, Error)
	assert_in("error_test.py", error.error)
	assert_in('raise ValueError("unexpected")', error.error)
	assert_in("ValueError: unexpected", error.error)
	assert_not_in("run_case", error.error)


def test_locates_failures_in_test_cases():
	with TemporaryDirectory() as temporary_dir:
		test_dir = Path(temporary_dir).joinpath("test")
		test_dir.mkdir()
		path = test_dir.joinpath("failure_test.py")
		path.write_text(
			"def test_direct():\n"
			"\tassert 1 == 2\n\n"
			"def test_helper():\n"
			"\tcheck(False)\n\n"
			"def test_multiline():\n"
			"\tcheck(\n"
			"\t\tFalse\n"
			"\t)\n\n"
			"def check(value):\n"
			"\tassert value\n"
		)

		printer = Printer(StringIO())
		reporter = Reporter(printer, Lines(printer), capture.Always())
		results = Runner(jobs=1).run(Suite.discover(test_dir), reporter)

	locations = []
	for result in results:
		failure = assert_is_instance(result, Fail)
		location = assert_not_none(failure.location)
		assert_eq(location.path, path.resolve())
		locations.append((location.line, location.source))
	assert_eq(
		locations,
		[
			(2, "assert 1 == 2"),
			(5, "check(False)"),
			(8, "check(\n\tFalse\n)"),
		],
	)
