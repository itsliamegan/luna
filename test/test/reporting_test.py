from contextlib import redirect_stdout
from io import StringIO

from luna.test import Case, Error, Test
from luna.test.assertion import assert_eq, assert_that
from luna.test.reporting import report
from luna.test.runner import EmptyFilter


def test_error_traceback_is_indented():
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


def test_results_are_reported_in_test_and_case_declaration_order():
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
