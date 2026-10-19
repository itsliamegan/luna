from io import StringIO

from luna.printer import Printer
from luna.test.assertion import assert_eq


def test_writes_text_unchanged_without_indentation():
	stream = StringIO()
	printer = Printer(stream)

	printer.write("first line\nsecond line\n")

	assert_eq(stream.getvalue(), "first line\nsecond line\n")


def test_indents_each_line_of_multiline_text():
	stream = StringIO()
	printer = Printer(stream)

	with printer.indented():
		printer.write("first line\nsecond line\n")

	assert_eq(stream.getvalue(), "\tfirst line\n\tsecond line\n")


def test_leaves_empty_lines_unindented():
	stream = StringIO()
	printer = Printer(stream)

	with printer.indented():
		printer.write("first line\n\nsecond line\n")

	assert_eq(stream.getvalue(), "\tfirst line\n\n\tsecond line\n")


def test_stacks_nested_prefixes():
	stream = StringIO()
	printer = Printer(stream)

	with printer.indented():
		printer.write("outer\n")
		with printer.indented("    "):
			printer.write("inner\n")
		printer.write("outer again\n")

	assert_eq(stream.getvalue(), "\touter\n\t    inner\n\touter again\n")


def test_continues_a_line_without_indenting_it_again():
	stream = StringIO()
	printer = Printer(stream)

	with printer.indented():
		printer.write("first ")
		printer.write("line\n")

	assert_eq(stream.getvalue(), "\tfirst line\n")


def test_indents_after_ending_a_line():
	stream = StringIO()
	printer = Printer(stream)

	with printer.indented():
		printer.write("first line")
		printer.end_line()
		printer.write("second line")

	assert_eq(stream.getvalue(), "\tfirst line\n\tsecond line")
