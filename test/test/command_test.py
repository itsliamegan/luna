from contextlib import redirect_stdout
from io import StringIO
import os
from pathlib import Path
from tempfile import TemporaryDirectory

from luna.cli.runnable import Failure
from luna.test.assertion import assert_in, assert_not_in, assert_raises
from luna.test.command import LunaTest


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

	assert_in("unit/models/user_test:test_create", output.getvalue())


def test_imports_modules_from_the_project_root():
	with TemporaryDirectory() as temporary_dir:
		root = Path(temporary_dir)
		root.joinpath("shared.py").write_text("VALUE = 1\n")
		test_dir = root.joinpath("test")
		test_dir.mkdir()
		test_dir.joinpath("user_test.py").write_text(
			"from shared import VALUE\n\ndef test_create():\n\tassert VALUE == 1\n"
		)

		cwd = Path.cwd()
		output = StringIO()
		try:
			with redirect_stdout(output):
				os.chdir(root)
				LunaTest(jobs=1).run()
		finally:
			os.chdir(cwd)

	assert_in("user_test:test_create", output.getvalue())


def test_runs_only_files_matching_the_pattern():
	with TemporaryDirectory() as temporary_dir:
		root = Path(temporary_dir)
		test_dir = root.joinpath("test")
		test_dir.mkdir()
		test_dir.joinpath("user_test.py").write_text("def test_create():\n\tpass\n")
		test_dir.joinpath("order_test.py").write_text("def test_place():\n\tpass\n")

		cwd = Path.cwd()
		output = StringIO()
		try:
			with redirect_stdout(output):
				os.chdir(root)
				LunaTest(pattern="order", jobs=1).run()
		finally:
			os.chdir(cwd)

	assert_in("order_test:test_place", output.getvalue())
	assert_not_in("user_test:test_create", output.getvalue())


def test_fails_when_no_tests_are_found():
	with TemporaryDirectory() as temporary_dir:
		root = Path(temporary_dir)
		root.joinpath("test").mkdir()

		cwd = Path.cwd()
		try:
			os.chdir(root)
			with assert_raises(Failure):
				LunaTest(jobs=1).run()
		finally:
			os.chdir(cwd)


def test_fails_when_no_tests_match_the_pattern():
	with TemporaryDirectory() as temporary_dir:
		root = Path(temporary_dir)
		test_dir = root.joinpath("test")
		test_dir.mkdir()
		test_dir.joinpath("user_test.py").write_text("def test_create():\n\tpass\n")

		cwd = Path.cwd()
		try:
			os.chdir(root)
			with assert_raises(Failure):
				LunaTest(pattern="order", jobs=1).run()
		finally:
			os.chdir(cwd)
