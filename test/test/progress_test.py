from io import StringIO
from pathlib import Path

from luna import ansi
from luna.ansi import Escape
from luna.printer import Printer
from luna.test import Error, Fail, Output, Pass
from luna.test.assertion import assert_eq
from luna.test.group import Group
from luna.test.progress import Lines
from luna.test.test import Test


def test_writes_a_line_per_result():
	group = Group(
		"user_test",
		Path("test", "user_test.py"),
		[Test("test_create"), Test("test_update"), Test("test_delete")],
	)
	results = [
		Pass("user_test", "test_create", Output("", "")),
		Fail("user_test", "test_update", "", Output("", "")),
		Error("user_test", "test_delete", "ValueError\n", Output("", "")),
	]
	stream = StringIO()
	progress = Lines(Printer(stream))

	progress.advance(group, results)
	progress.finish()

	assert_eq(
		stream.getvalue().splitlines(),
		[
			f"{ansi.escape(Escape.GREEN, "PASS")}\tuser_test:test_create",
			f"{ansi.escape(Escape.RED, "FAIL")}\tuser_test:test_update",
			f"{ansi.escape(Escape.YELLOW, "ERROR")}\tuser_test:test_delete",
		],
	)
