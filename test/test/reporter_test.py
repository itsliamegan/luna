from datetime import timedelta
from io import StringIO
from pathlib import Path

from luna import ansi
from luna.ansi import Escape
from luna.printer import Printer
from luna.test.assertion import assert_eq, assert_in, assert_not_in
from luna.test.capture import AlwaysCapture, NeverCapture, PassCapture
from luna.test.group import Group
from luna.test.location import Location
from luna.test.output import Output
from luna.test.progress import Lines
from luna.test.reporter import Reporter
from luna.test.result import Error, Fail, Pass
from luna.test.test import Test


def test_indents_multiline_errors():
	group = Group("user_test", Path("test", "user_test.py"), [Test("test_create")])
	result = Error(
		"user_test",
		"test_create",
		"first line\nsecond line\n",
		Output("", ""),
	)
	stream = StringIO()
	printer = Printer(stream)
	reporter = Reporter(printer, Lines(printer), AlwaysCapture())

	reporter.group_finished(group, [result])
	reporter.suite_finished(timedelta(seconds=1))

	block = stream.getvalue().split("\n\n")[1]
	assert_eq(
		block.splitlines(),
		[
			f"{ansi.escape(Escape.YELLOW, "ERROR")}\tuser_test:test_create",
			"\tfirst line",
			"\tsecond line",
		],
	)


def test_reports_failure_locations():
	group = Group("user_test", Path("test", "user_test.py"), [Test("test_create")])
	location = Location(
		Path.cwd().joinpath("test", "user_test.py"),
		7,
		"assert (\n\t1 == 2\n)",
	)
	result = Fail(
		"user_test",
		"test_create",
		"expected 1, got 2",
		Output("", ""),
		location=location,
	)
	stream = StringIO()
	printer = Printer(stream)
	reporter = Reporter(printer, Lines(printer), AlwaysCapture())

	reporter.group_finished(group, [result])
	reporter.suite_finished(timedelta(seconds=1))

	block = stream.getvalue().split("\n\n")[1]
	assert_eq(
		block.splitlines(),
		[
			f"{ansi.escape(Escape.RED, "FAIL")}\tuser_test:test_create",
			"\ttest/user_test.py:7",
			"\t    assert (",
			"\t    \t1 == 2",
			"\t    )",
			"\texpected 1, got 2",
		],
	)


def test_captures_all_output():
	group = Group(
		"user_test",
		Path("test", "user_test.py"),
		[Test("test_create"), Test("test_update"), Test("test_delete")],
	)
	results = [
		Pass("user_test", "test_create", Output("passing output\n", "")),
		Fail("user_test", "test_update", "", Output("", "failing output\n")),
		Error("user_test", "test_delete", "ValueError\n", Output("error output\n", "")),
	]
	stream = StringIO()
	printer = Printer(stream)
	reporter = Reporter(printer, Lines(printer), AlwaysCapture())

	reporter.group_finished(group, results)
	reporter.suite_finished(timedelta(seconds=1))

	output = stream.getvalue()
	assert_not_in("passing output", output)
	assert_not_in("failing output", output)
	assert_not_in("error output", output)


def test_captures_failing_output():
	group = Group(
		"user_test",
		Path("test", "user_test.py"),
		[Test("test_create"), Test("test_update"), Test("test_delete")],
	)
	results = [
		Pass("user_test", "test_create", Output("passing output\n", "")),
		Fail("user_test", "test_update", "", Output("", "failing output\n")),
		Error("user_test", "test_delete", "ValueError\n", Output("error output\n", "")),
	]
	stream = StringIO()
	printer = Printer(stream)
	reporter = Reporter(printer, Lines(printer), PassCapture())

	reporter.group_finished(group, results)
	reporter.suite_finished(timedelta(seconds=1))

	output = stream.getvalue()
	assert_not_in("passing output", output)
	assert_in("\tfailing output\n", output)
	assert_in("\terror output\n", output)


def test_captures_no_output():
	group = Group(
		"user_test",
		Path("test", "user_test.py"),
		[Test("test_create"), Test("test_update"), Test("test_delete")],
	)
	results = [
		Pass("user_test", "test_create", Output("passing output\n", "")),
		Fail("user_test", "test_update", "", Output("", "failing output\n")),
		Error("user_test", "test_delete", "ValueError\n", Output("error output\n", "")),
	]
	stream = StringIO()
	printer = Printer(stream)
	reporter = Reporter(printer, Lines(printer), NeverCapture())

	reporter.group_finished(group, results)
	reporter.suite_finished(timedelta(seconds=1))

	output = stream.getvalue()
	assert_in("\tpassing output\n", output)
	assert_in("\tfailing output\n", output)
	assert_in("\terror output\n", output)


def test_omits_blocks_for_passes_without_output():
	group = Group("user_test", Path("test", "user_test.py"), [Test("test_create")])
	result = Pass("user_test", "test_create", Output("", ""))
	stream = StringIO()
	printer = Printer(stream)
	reporter = Reporter(printer, Lines(printer), NeverCapture())

	reporter.group_finished(group, [result])
	reporter.suite_finished(timedelta(seconds=1))

	sections = stream.getvalue().split("\n\n")
	assert_eq(len(sections), 2)


def test_separates_sections_and_blocks_with_blank_lines():
	group = Group(
		"user_test",
		Path("test", "user_test.py"),
		[Test("test_create"), Test("test_update"), Test("test_delete")],
	)
	results = [
		Pass("user_test", "test_create", Output("", "")),
		Fail("user_test", "test_update", "expected 1, got 2", Output("", "")),
		Error("user_test", "test_delete", "ValueError\n", Output("", "")),
	]
	stream = StringIO()
	printer = Printer(stream)
	reporter = Reporter(printer, Lines(printer), AlwaysCapture())

	reporter.group_finished(group, results)
	reporter.suite_finished(timedelta(seconds=1))

	sections = stream.getvalue().split("\n\n")
	assert_eq(len(sections), 4)
	assert_in("user_test:test_update", sections[1])
	assert_in("user_test:test_delete", sections[2])
	assert_in("in 1.00s", sections[3])


def test_counts_results_by_status():
	group = Group(
		"user_test",
		Path("test", "user_test.py"),
		[
			Test("test_create"),
			Test("test_update"),
			Test("test_delete"),
			Test("test_archive"),
		],
	)
	results = [
		Pass("user_test", "test_create", Output("", "")),
		Fail("user_test", "test_update", "", Output("", "")),
		Error("user_test", "test_delete", "ValueError\n", Output("", "")),
		Error("user_test", "test_archive", "KeyError\n", Output("", "")),
	]
	stream = StringIO()
	printer = Printer(stream)
	reporter = Reporter(printer, Lines(printer), AlwaysCapture())

	reporter.group_finished(group, results)
	reporter.suite_finished(timedelta(seconds=1.5))

	summary = stream.getvalue().splitlines()[-1]
	assert_eq(
		summary,
		f"{ansi.escape(Escape.GREEN, "1 passed")}, "
		f"{ansi.escape(Escape.RED, "1 failed")}, "
		f"{ansi.escape(Escape.YELLOW, "2 errors")} in 1.50s",
	)


def test_leaves_out_zero_counts():
	group = Group("user_test", Path("test", "user_test.py"), [Test("test_create")])
	result = Pass("user_test", "test_create", Output("", ""))
	stream = StringIO()
	printer = Printer(stream)
	reporter = Reporter(printer, Lines(printer), AlwaysCapture())

	reporter.group_finished(group, [result])
	reporter.suite_finished(timedelta(seconds=0.25))

	summary = stream.getvalue().splitlines()[-1]
	assert_eq(summary, f"{ansi.escape(Escape.GREEN, "1 passed")} in 0.25s")
