from contextlib import redirect_stdout
from io import StringIO
import sys

from luna.test import Case, Error, Test
from luna.test.assertion import assert_eq, assert_that
from luna.test.reporting import Capture, report
from luna.test.runner import EmptyFilter


def test_indents_error_traceback():
	def raise_error():
		raise ValueError("unexpected")

	case = Case("test_error_traceback_is_indented", raise_error)
	test = Test("reporting_test", [case])
	result = test.run(EmptyFilter())[0]
	assert isinstance(result, Error)

	output = StringIO()
	with redirect_stdout(output):
		report([result])
	lines = output.getvalue().splitlines()

	assert_that("ERROR" in lines[0])
	assert_that(lines[1].startswith("\tTraceback (most recent call last):"))
	assert_that(all(line.startswith("\t") for line in lines[1:]))
	assert_that("self.impl()" not in output.getvalue())
	assert_eq(lines[-1], "\tValueError: unexpected")


def test_sorts_results_by_test_name_and_case_index():
	zebra_test = Test("zebra_test", [Case("test_case", lambda: None)])
	ant_test = Test(
		"ant_test",
		[Case("test_second", lambda: None), Case("test_first", lambda: None)],
	)
	zebra_result = zebra_test.run(EmptyFilter())[0]
	second_ant_result, first_ant_result = ant_test.run(EmptyFilter())

	output = StringIO()
	with redirect_stdout(output):
		report([zebra_result, first_ant_result, second_ant_result])

	reported_names = [
		line.split("\t", maxsplit=1)[1] for line in output.getvalue().splitlines()
	]
	assert_eq(
		reported_names,
		["ant_test:test_second", "ant_test:test_first", "zebra_test:test_case"],
	)


def test_captures_all_output():
	def passing():
		print("passing output")

	def failing():
		print("failing output", file=sys.stderr)
		raise AssertionError

	def erroring():
		print("error output")
		raise ValueError

	results = [
		Case("pass", passing).run("test", 0),
		Case("fail", failing).run("test", 1),
		Case("error", erroring).run("test", 2),
	]
	stream = StringIO()
	with redirect_stdout(stream):
		report(results, Capture.ALWAYS)
	output = stream.getvalue()

	assert_that("passing ouput" not in output)
	assert_that("failing output" not in output)
	assert_that("error output" not in output)


def test_captures_failing_output():
	def passing():
		print("passing output")

	def failing():
		print("failing output", file=sys.stderr)
		raise AssertionError

	def erroring():
		print("error output")
		raise ValueError

	results = [
		Case("passing", passing).run("test", 0),
		Case("failing", failing).run("test", 1),
		Case("erroring", erroring).run("test", 2),
	]
	stream = StringIO()
	with redirect_stdout(stream):
		report(results, Capture.PASS)
	output = stream.getvalue()

	assert_that("passing output" not in output)
	assert_that("failing output" in output)
	assert_that("error output" in output)


def test_captures_no_output():
	def passing():
		print("passing output")

	def failing():
		print("failing output", file=sys.stderr)
		raise AssertionError

	def erroring():
		print("error output")
		raise ValueError

	results = [
		Case("passing", passing).run("test", 0),
		Case("failing", failing).run("test", 1),
		Case("erroring", erroring).run("test", 2),
	]
	stream = StringIO()
	with redirect_stdout(stream):
		report(results, Capture.NEVER)
	output = stream.getvalue()

	assert_that("passing output" in output)
	assert_that("failing output" in output)
	assert_that("error output" in output)
