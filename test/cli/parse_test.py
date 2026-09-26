from contextlib import redirect_stderr, redirect_stdout
from enum import StrEnum
from io import StringIO
from typing import cast

from luna.cli import Command, HelpRequested, ParseError, Program, argument, option
from luna.cli.parse import parse
from luna.test.assertion import assert_eq, assert_not, assert_raises, assert_that


class Mode(StrEnum):
	SAFE = "safe"
	FAST = "fast"


class Copy(Program):
	"""Copy a file."""

	name = "copy"
	source: str = argument(help="file to copy")
	destination: str | None = argument(None, help="where to copy it")
	count: int = option(1, short="c", help="number of copies")
	verbose: bool = option(short="v")
	all: bool = option(short="a")
	binary: bool = option(short="b")
	tag: list[str] = option(["default"], short="t")

	def run(self):
		pass


def help_for(program: type[Program], argv: list[str]) -> str:
	with assert_raises(HelpRequested) as raised:
		parse(program, argv)
	return cast(HelpRequested, raised.exception).help


def parse_error(program: type[Program], argv: list[str]) -> ParseError:
	with assert_raises(ParseError) as raised:
		parse(program, argv)
	return cast(ParseError, raised.exception)


def test_parses_arguments_and_options():
	result = parse(
		Copy,
		[
			"input.txt",
			"--count",
			"2",
			"-v",
			"output.txt",
			"--tag",
			"one",
			"-t=two",
			"--tag=three",
		],
	)

	assert_that(result.program is Copy)
	assert_eq(result.command, None)
	assert_eq(
		result.values,
		{
			"source": "input.txt",
			"destination": "output.txt",
			"count": 2,
			"verbose": True,
			"all": False,
			"binary": False,
			"tag": ["one", "two", "three"],
		},
	)


def test_applies_defaults_when_omitted():
	assert_eq(
		parse(Copy, ["input.txt"]).values,
		{
			"source": "input.txt",
			"destination": None,
			"count": 1,
			"verbose": False,
			"all": False,
			"binary": False,
			"tag": ["default"],
		},
	)


def test_parses_option_forms():
	for argv in [
		["--count", "2"],
		["--count=2"],
		["-c", "2"],
		["-c=2"],
		["-c2"],
		["--cou", "2"],
	]:
		assert_eq(parse(Copy, [*argv, "input.txt"]).values["count"], 2)


def test_groups_short_flags():
	values = parse(Copy, ["-vab", "input.txt"]).values

	assert_eq(
		[values["verbose"], values["all"], values["binary"]],
		[True, True, True],
	)


def test_ends_option_parsing_at_terminator():
	values = parse(Copy, ["-c", "-2", "--", "-input", "--count"]).values

	assert_eq(values["count"], -2)
	assert_eq(values["source"], "-input")
	assert_eq(values["destination"], "--count")


def test_rejects_invalid_input():
	for argv in [
		[],
		["input.txt", "--unknown"],
		["input.txt", "--count", "two"],
		["input.txt", "--verbose=yes"],
		["input.txt", "output.txt", "extra"],
	]:
		error = parse_error(Copy, argv)
		assert_that(error.usage.startswith("usage: copy"))


def test_parses_value_kinds():
	class Kinds(Program):
		name = "kinds"
		positional: str = argument()
		specified: int = option(1)
		plain: int = 2
		required: int

		def run(self):
			pass

	assert_eq(
		parse(Kinds, ["text", "--required", "3"]).values,
		{"positional": "text", "specified": 1, "plain": 2, "required": 3},
	)
	assert_eq(
		parse(Kinds, ["--plain", "4", "text", "--specified=5", "--required=6"]).values,
		{"positional": "text", "specified": 5, "plain": 4, "required": 6},
	)
	assert_that("--required" in parse_error(Kinds, ["text"]).message)


def test_parses_nullable_and_enum_values():
	class Values(Program):
		name = "values"
		mode: Mode = argument(Mode.SAFE)
		limit: int | None = None
		fallback: Mode | None = option(None)
		modes: list[Mode] = option()

		def run(self):
			pass

	assert_eq(
		parse(Values, []).values,
		{"mode": Mode.SAFE, "limit": None, "fallback": None, "modes": []},
	)
	assert_eq(
		parse(
			Values,
			["fast", "--limit=3", "--fallback=safe", "--modes=fast", "--modes=safe"],
		).values,
		{
			"mode": Mode.FAST,
			"limit": 3,
			"fallback": Mode.SAFE,
			"modes": [Mode.FAST, Mode.SAFE],
		},
	)
	assert_that(
		"invalid choice: 'slow' (choose from safe, fast)"
		in parse_error(Values, ["slow"]).message
	)


def test_uses_a_new_list_default_for_each_parse():
	class Lists(Program):
		name = "lists"
		empty: list[str] = option()
		given: list[int] = option([1])

		def run(self):
			pass

	first = parse(Lists, []).values
	cast(list[str], first["empty"]).append("changed")
	cast(list[int], first["given"]).append(2)
	second = parse(Lists, []).values

	assert_eq(second, {"empty": [], "given": [1]})


def test_uses_names_verbatim():
	class Export(Program):
		"""Export a report."""

		name = "export_report"
		output_path: str = argument(help="where to write")
		page_size: int = option(10, help="rows per page")

		def run(self):
			pass

	values = parse(Export, ["out.txt", "--page_size", "20"]).values
	help = help_for(Export, ["--help"])

	assert_eq(values, {"output_path": "out.txt", "page_size": 20})
	assert_that(help.startswith("usage: export_report"))
	assert_that("<output_path>" in help)
	assert_that("--page_size <page_size>" in help)
	assert_not("page-size" in help)
	assert_that(
		"--page_size" in parse_error(Export, ["out.txt", "--page_size"]).message
	)


def test_returns_help_message():
	help = help_for(Copy, ["--help"])

	assert_eq(help_for(Copy, ["-h"]), help)
	for text in [
		"usage: copy",
		"Copy a file.",
		"<source>",
		"file to copy",
		"--count, -c <count>",
		"number of copies",
	]:
		assert_that(text in help)


def test_lists_enum_choices_in_help():
	class Choose(Program):
		name = "choose"
		mode: Mode = option(Mode.SAFE, help="how to 100% run")
		modes: list[Mode] = option()

		def run(self):
			pass

	help = help_for(Choose, ["--help"])

	assert_that("how to 100% run (choices: safe, fast)" in help)
	assert_that("--modes <modes>  choices: safe, fast" in help)


def test_preserves_docstring_layout_in_help():
	class Layout(Program):
		"""
		Summarize the input.

		Reads every line.
		"""

		name = "layout"

		def run(self):
			pass

	help = help_for(Layout, ["--help"])

	assert_that("Summarize the input.\n\nReads every line.\n" in help)


class Show(Command):
	"""Show a file."""

	name = "show-file"
	verbose: bool = option(short="v")

	def run(self):
		pass


class Move(Command):
	"""Move a file."""

	name = "move"
	source: str = argument(help="file to move")
	force: bool = option(short="f", help="overwrite existing files")
	tag: list[str] = option(short="t")

	def run(self):
		pass


class Files(Program):
	"""Manage files."""

	name = "files"
	commands = [Move, Show]  # noqa: RUF012


def test_selects_and_parses_command():
	move = parse(Files, ["move", "input.txt", "-f", "-t", "one", "-t=two"])
	show = parse(Files, ["show-file", "-v"])

	assert_that(move.program is Files)
	assert_that(move.command is Move)
	assert_eq(
		move.values, {"source": "input.txt", "force": True, "tag": ["one", "two"]}
	)
	assert_that(show.command is Show)
	assert_eq(show.values, {"verbose": True})


def test_reports_command_errors():
	for argv in [[], ["unknown"], ["--unknown"], ["-v", "show-file"], ["--", "move"]]:
		error = parse_error(Files, argv)
		assert_that(error.usage.startswith("usage: files"))
		assert_not("files move" in error.usage)

	error = parse_error(Files, ["move"])
	assert_that(error.usage.startswith("usage: files move"))


def test_raises_program_and_command_help():
	program_help = help_for(Files, ["-h"])
	command_help = help_for(Files, ["move", "--help"])

	assert_eq(help_for(Files, ["--help", "move"]), program_help)
	for text in [
		"usage: files",
		"Manage files.",
		"move",
		"Move a file.",
		"show-file",
		"Show a file.",
	]:
		assert_that(text in program_help)
	for text in [
		"usage: files move",
		"Move a file.",
		"<source>",
		"file to move",
		"--force, -f",
		"overwrite existing files",
	]:
		assert_that(text in command_help)


def test_omits_missing_descriptions():
	class Plain(Program):
		name = "plain"

		def run(self):
			pass

	assert_eq(
		help_for(Plain, ["--help"]),
		"usage: plain [--help]\n\noptions:\n  --help, -h  show this help message and exit\n",
	)


def test_doesnt_write_output():
	stdout = StringIO()
	stderr = StringIO()

	with redirect_stdout(stdout), redirect_stderr(stderr):
		for program, argv in [
			(Copy, []),
			(Files, []),
			(Files, ["move"]),
		]:
			with assert_raises(ParseError):
				parse(program, argv)
		for program, argv in [
			(Copy, ["--help"]),
			(Files, ["--help"]),
			(Files, ["move", "--help"]),
		]:
			with assert_raises(HelpRequested):
				parse(program, argv)

	assert_eq(stdout.getvalue(), "")
	assert_eq(stderr.getvalue(), "")
