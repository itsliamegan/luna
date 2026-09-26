from contextlib import redirect_stdout
from io import StringIO
import os
from pathlib import Path
from tempfile import TemporaryDirectory

from luna.test import Error, Pass
from luna.test.assertion import assert_eq, assert_that
from luna.test.runner import EmptyFilter, LunaTest, Runner, discover


def test_discovers_nested_tests():
	with TemporaryDirectory() as temporary_dir:
		test_dir = Path(temporary_dir).joinpath("test")
		path = test_dir.joinpath("unit", "models", "user_test.py")
		path.parent.mkdir(parents=True)
		path.write_text("def test_create():\n\tpass\n")

		suite = discover(test_dir)

	assert_eq(len(suite.tests), 1)
	assert_eq(suite.tests[0].name, "unit/models/user_test")
	assert_eq(suite.tests[0].cases[0].name, "test_create")


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

		results = Runner(jobs=2).run(discover(test_dir), EmptyFilter())

		assert_that(all(isinstance(result, Pass) for result in results))
		assert_that(first_pid.read_text() != second_pid.read_text())


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

		suite = discover(test_dir)
		results = Runner(jobs=1).run(suite, EmptyFilter())

		assert_that(all(isinstance(result, Pass) for result in results))
		assert_eq(imports.read_text(), "2")


def test_formats_error_tracebacks_without_runner_frames():
	with TemporaryDirectory() as temporary_dir:
		test_dir = Path(temporary_dir).joinpath("test")
		test_dir.mkdir()
		test_dir.joinpath("error_test.py").write_text(
			'def test_error():\n\traise ValueError("unexpected")\n'
		)

		results = Runner(jobs=1).run(discover(test_dir), EmptyFilter())

	result = results[0]
	assert isinstance(result, Error)
	assert_that("error_test.py" in result.error)
	assert_that('raise ValueError("unexpected")' in result.error)
	assert_that("ValueError: unexpected" in result.error)
	assert_that("run_case" not in result.error)


def test_reports_nested_test_names():
	with TemporaryDirectory() as temporary_dir:
		root = Path(temporary_dir)
		test_dir = root.joinpath("test", "unit", "models")
		test_dir.mkdir(parents=True)
		test_dir.joinpath("user_test.py").write_text("def test_create():\n\tpass\n")

		cwd = Path.cwd()
		output = StringIO()
		try:
			with redirect_stdout(output):
				os.chdir(root)
				LunaTest(jobs=1).run()
		finally:
			os.chdir(cwd)

	assert_that("unit/models/user_test:test_create" in output.getvalue())
