from contextlib import redirect_stdout
from io import StringIO
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

from luna.test.assertion import assert_that
from luna.test.runner import main


def test_nested_test_names_use_slashes():
	with TemporaryDirectory() as temporary_dir:
		root = Path(temporary_dir)
		test_dir = root.joinpath("test").joinpath("unit").joinpath("models")
		test_dir.mkdir(parents=True)
		test_dir.joinpath("user_test.py").write_text("def test_create():\n\tpass\n")

		cwd = Path.cwd()
		argv = sys.argv
		output = StringIO()
		try:
			sys.argv = ["test"]
			with redirect_stdout(output):
				os.chdir(root)
				main()
		finally:
			os.chdir(cwd)
			sys.argv = argv

	assert_that("unit/models/user_test:test_create" in output.getvalue())
