from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from luna.test import Error, Fail, Location, Output, Pass
from luna.test.assertion import assert_eq, assert_in, assert_not_in
from luna.test.reporting import Capture, report


def test_indents_multiline_errors():
	result = Error(
		"reporting_test",
		"test_error",
		"first line\nsecond line\n",
		Output("", ""),
	)

	output = StringIO()
	with redirect_stdout(output):
		report([result])
	lines = output.getvalue().splitlines()

	assert_in("ERROR", lines[0])
	assert_eq(lines[1:], ["\tfirst line", "\tsecond line"])


def test_reports_failure_locations():
	location = Location(
		Path.cwd().joinpath("test", "example_test.py"),
		7,
		"assert (\n\t1 == 2\n)",
	)
	result = Fail(
		"example_test",
		"test_case",
		"",
		Output("", ""),
		location=location,
	)

	output = StringIO()
	with redirect_stdout(output):
		report([result])
	lines = output.getvalue().splitlines()

	assert_eq(
		lines[1:],
		[
			"\ttest/example_test.py:7",
			"\t    assert (",
			"\t    \t1 == 2",
			"\t    )",
		],
	)


def test_captures_all_output():
	results = [
		Pass("test", "passing", Output("passing output\n", "")),
		Fail("test", "failing", "", Output("", "failing output\n")),
		Error("test", "erroring", "ValueError\n", Output("error output\n", "")),
	]
	stream = StringIO()
	with redirect_stdout(stream):
		report(results, Capture.ALWAYS)
	output = stream.getvalue()

	assert_not_in("passing output", output)
	assert_not_in("failing output", output)
	assert_not_in("error output", output)


def test_captures_failing_output():
	results = [
		Pass("test", "passing", Output("passing output\n", "")),
		Fail("test", "failing", "", Output("", "failing output\n")),
		Error("test", "erroring", "ValueError\n", Output("error output\n", "")),
	]
	stream = StringIO()
	with redirect_stdout(stream):
		report(results, Capture.PASS)
	output = stream.getvalue()

	assert_not_in("passing output", output)
	assert_in("failing output", output)
	assert_in("error output", output)


def test_captures_no_output():
	results = [
		Pass("test", "passing", Output("passing output\n", "")),
		Fail("test", "failing", "", Output("", "failing output\n")),
		Error("test", "erroring", "ValueError\n", Output("error output\n", "")),
	]
	stream = StringIO()
	with redirect_stdout(stream):
		report(results, Capture.NEVER)
	output = stream.getvalue()

	assert_in("passing output", output)
	assert_in("failing output", output)
	assert_in("error output", output)
