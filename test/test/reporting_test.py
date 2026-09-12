from contextlib import redirect_stdout
from io import StringIO

from luna.test import Error, Fail, Output, Pass
from luna.test.assertion import assert_eq, assert_that
from luna.test.reporting import Capture, report


def test_indents_multiline_errors():
	result = Error(
		"reporting_test",
		"test_error",
		0,
		"first line\nsecond line\n",
		Output("", ""),
	)

	output = StringIO()
	with redirect_stdout(output):
		report([result])
	lines = output.getvalue().splitlines()

	assert_that("ERROR" in lines[0])
	assert_eq(lines[1:], ["\tfirst line", "\tsecond line"])


def test_sorts_results_by_test_name_and_case_index():
	output = Output("", "")
	results = [
		Pass("zebra_test", "test_case", 0, output),
		Pass("ant_test", "test_first", 1, output),
		Pass("ant_test", "test_second", 0, output),
	]

	stream = StringIO()
	with redirect_stdout(stream):
		report(results)

	reported_names = [
		line.split("\t", maxsplit=1)[1] for line in stream.getvalue().splitlines()
	]
	assert_eq(
		reported_names,
		["ant_test:test_second", "ant_test:test_first", "zebra_test:test_case"],
	)


def test_captures_all_output():
	results = [
		Pass("test", "passing", 0, Output("passing output\n", "")),
		Fail("test", "failing", 1, "", Output("", "failing output\n")),
		Error("test", "erroring", 2, "ValueError\n", Output("error output\n", "")),
	]
	stream = StringIO()
	with redirect_stdout(stream):
		report(results, Capture.ALWAYS)
	output = stream.getvalue()

	assert_that("passing output" not in output)
	assert_that("failing output" not in output)
	assert_that("error output" not in output)


def test_captures_failing_output():
	results = [
		Pass("test", "passing", 0, Output("passing output\n", "")),
		Fail("test", "failing", 1, "", Output("", "failing output\n")),
		Error("test", "erroring", 2, "ValueError\n", Output("error output\n", "")),
	]
	stream = StringIO()
	with redirect_stdout(stream):
		report(results, Capture.PASS)
	output = stream.getvalue()

	assert_that("passing output" not in output)
	assert_that("failing output" in output)
	assert_that("error output" in output)


def test_captures_no_output():
	results = [
		Pass("test", "passing", 0, Output("passing output\n", "")),
		Fail("test", "failing", 1, "", Output("", "failing output\n")),
		Error("test", "erroring", 2, "ValueError\n", Output("error output\n", "")),
	]
	stream = StringIO()
	with redirect_stdout(stream):
		report(results, Capture.NEVER)
	output = stream.getvalue()

	assert_that("passing output" in output)
	assert_that("failing output" in output)
	assert_that("error output" in output)
