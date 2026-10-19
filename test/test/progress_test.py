from io import StringIO
from pathlib import Path

from luna import ansi
from luna.ansi import Escape
from luna.printer import Printer
from luna.test import progress
from luna.test.assertion import assert_eq
from luna.test.group import Group
from luna.test.result import Error, Fail, Pass
from luna.test.test import Test


def test_writes_a_dot_per_result():
	group = Group(
		"user_test",
		Path("test", "user_test.py"),
		[Test("test_create"), Test("test_update"), Test("test_delete")],
	)
	results = [
		Pass(Test("test_create"), ""),
		Fail(Test("test_update"), "", "", None),
		Error(Test("test_delete"), "", "ValueError\n"),
	]
	stream = StringIO()
	dots = progress.Dots(Printer(stream))

	dots.advance(group, results)

	assert_eq(
		stream.getvalue(),
		ansi.escape(Escape.GREEN, ".")
		+ ansi.escape(Escape.RED, "F")
		+ ansi.escape(Escape.YELLOW, "E"),
	)


def test_continues_dots_across_groups_and_ends_the_row():
	user_group = Group("user_test", Path("test", "user_test.py"), [Test("test_create")])
	order_group = Group(
		"order_test", Path("test", "order_test.py"), [Test("test_place")]
	)
	stream = StringIO()
	dots = progress.Dots(Printer(stream))

	dots.advance(user_group, [Pass(Test("test_create"), "")])
	dots.advance(order_group, [Pass(Test("test_place"), "")])
	dots.finish()

	dot = ansi.escape(Escape.GREEN, ".")
	assert_eq(stream.getvalue(), f"{dot}{dot}\n")


def test_writes_a_line_per_result():
	group = Group(
		"user_test",
		Path("test", "user_test.py"),
		[Test("test_create"), Test("test_update"), Test("test_delete")],
	)
	results = [
		Pass(Test("test_create"), ""),
		Fail(Test("test_update"), "", "", None),
		Error(Test("test_delete"), "", "ValueError\n"),
	]
	stream = StringIO()
	lines = progress.Lines(Printer(stream))

	lines.advance(group, results)
	lines.finish()

	assert_eq(
		stream.getvalue().splitlines(),
		[
			f"{ansi.escape(Escape.GREEN, "PASS")}\tuser_test:test_create",
			f"{ansi.escape(Escape.RED, "FAIL")}\tuser_test:test_update",
			f"{ansi.escape(Escape.YELLOW, "ERROR")}\tuser_test:test_delete",
		],
	)
