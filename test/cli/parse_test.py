from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from typing import cast

from luna.cli import Argument, Command, Option, Program
from luna.cli.parse import HelpRequested, ParseError, parse
from luna.test.assertion import assert_eq, assert_not, assert_raises, assert_that


def noop(**values: object):
	pass


def test_parses_arguments_and_options():
	program = Program(
		"copy",
		noop,
		arguments=[
			Argument("source"),
			Argument("destination", required=False),
			Argument("mode", required=False, default="safe"),
		],
		options=[
			Option("count", short="c", type=int, default=1),
			Option("verbose", short="v", type=bool),
			Option("all", short="a", type=bool),
			Option("binary", short="b", type=bool),
			Option("tag", short="t", type=list[str], default=["default"]),
		],
	)

	result = parse(
		program,
		[
			"input.txt",
			"--count",
			"2",
			"-v",
			"-a",
			"-b",
			"output.txt",
			"fast",
			"--tag",
			"one",
			"-t=two",
			"--tag=three",
		],
	)

	assert_eq(
		result.values,
		{
			"source": "input.txt",
			"destination": "output.txt",
			"mode": "fast",
			"count": 2,
			"verbose": True,
			"all": True,
			"binary": True,
			"tag": ["one", "two", "three"],
		},
	)


def test_parses_option_forms_and_terminator():
	program = Program(
		"show",
		noop,
		arguments=[Argument("name")],
		options=[Option("count", short="c", type=int)],
	)

	for argv in [
		["--count", "2"],
		["--count=2"],
		["-c", "2"],
		["-c=2"],
	]:
		assert_eq(
			parse(program, [*argv, "document"]).values,
			{"name": "document", "count": 2},
		)

	assert_eq(
		parse(program, ["-c", "-2", "--", "-document"]).values,
		{"name": "-document", "count": -2},
	)


def test_rejects_invalid_input():
	program = Program(
		"copy",
		noop,
		arguments=[Argument("source")],
		options=[Option("count", type=int)],
	)

	for argv in [
		[],
		["input", "--unknown"],
		["input", "--count", "two"],
	]:
		with assert_raises(ParseError):
			parse(program, argv)

	with assert_raises(ParseError):
		parse(Program("copy", noop, options=[Option("required", required=True)]), [])


def test_returns_help_message():
	program = Program(
		"copy",
		noop,
		description="Copy a file.",
		arguments=[Argument("source", help="File to copy")],
		options=[Option("count", short="c", type=int, help="Number of copies")],
	)

	with assert_raises(HelpRequested) as raised:
		parse(program, ["--help"])

	help = cast(HelpRequested, raised.exception).help
	for text in [
		"Copy a file.",
		"source",
		"File to copy",
		"--count",
		"-c",
		"Number of copies",
	]:
		assert_that(text in help)


def test_selects_and_parses_command():
	copy = Command(
		"copy",
		noop,
		arguments=[Argument("source")],
		options=[
			Option("count", short="c", type=int, default=1),
			Option("tag", short="t", type=list[str]),
		],
	)
	show = Command("show", noop, options=[Option("verbose", short="v", type=bool)])
	program = Program("files", commands=[copy, show])

	copy_result = parse(program, ["copy", "input.txt", "-c=2", "-t", "one", "-t=two"])
	show_result = parse(program, ["show", "-v"])

	assert_eq(
		copy_result.values,
		{"source": "input.txt", "count": 2, "tag": ["one", "two"]},
	)
	assert_eq(show_result.values, {"verbose": True})


def test_reports_command_errors():
	program = Program(
		"files",
		commands=[
			Command("copy", noop, arguments=[Argument("source")]),
			Command("show", noop),
		],
	)

	for argv in [[], ["unknown"], ["--unknown"], ["--", "copy"]]:
		with assert_raises(ParseError) as raised:
			parse(program, argv)
		error = cast(ParseError, raised.exception)
		assert_that(error.usage.startswith("usage: files"))
		assert_not("files copy" in error.usage)

	with assert_raises(ParseError) as raised:
		parse(program, ["copy"])
	error = cast(ParseError, raised.exception)
	assert_that(error.usage.startswith("usage: files copy"))


def test_raises_program_and_command_help():
	program = Program(
		"files",
		description="Manage files.",
		commands=[
			Command(
				"copy",
				noop,
				description="Copy a file.",
				arguments=[Argument("source", help="File to copy")],
				options=[Option("force", short="f", type=bool, help="Overwrite")],
			),
			Command("show", noop, description="Show a file."),
		],
	)

	with assert_raises(HelpRequested) as top_level:
		parse(program, ["-h"])
	program_help = cast(HelpRequested, top_level.exception).help
	for text in [
		"Manage files.",
		"copy",
		"Copy a file.",
		"show",
		"Show a file.",
	]:
		assert_that(text in program_help)

	with assert_raises(HelpRequested) as command:
		parse(program, ["copy", "--help"])
	command_help = cast(HelpRequested, command.exception).help
	for text in [
		"Copy a file.",
		"source",
		"File to copy",
		"--force",
		"-f",
		"Overwrite",
	]:
		assert_that(text in command_help)


def test_doesnt_write_output():
	direct = Program("copy", noop, arguments=[Argument("source")])
	commands = Program(
		"files",
		commands=[Command("copy", noop, arguments=[Argument("source")])],
	)
	stdout = StringIO()
	stderr = StringIO()

	with redirect_stdout(stdout), redirect_stderr(stderr):
		with assert_raises(ParseError):
			parse(direct, [])
		with assert_raises(HelpRequested):
			parse(direct, ["--help"])
		with assert_raises(ParseError):
			parse(commands, [])
		with assert_raises(HelpRequested):
			parse(commands, ["--help"])
		with assert_raises(ParseError):
			parse(commands, ["copy"])
		with assert_raises(HelpRequested):
			parse(commands, ["copy", "--help"])

	assert_eq(stdout.getvalue(), "")
	assert_eq(stderr.getvalue(), "")
