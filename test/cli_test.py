from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from typing import cast

from luna.cli import Argument, Command, Option, Program
from luna.test.assertion import assert_eq, assert_raises, assert_that


def noop(**values: object):
	pass


def test_validates_program_structure():
	command = Command("copy", noop)
	with assert_raises(ValueError):
		Program("files", arguments=[Argument("source")], commands=[command])
	with assert_raises(ValueError):
		Program("files", options=[Option("verbose")], commands=[command])

	with assert_raises(ValueError):
		Program("show", noop, arguments=[Argument("value"), Argument("value")])
	with assert_raises(ValueError):
		Program(
			"show",
			noop,
			arguments=[Argument("value")],
			options=[Option("value")],
		)
	with assert_raises(ValueError):
		Command("show", noop, options=[Option("__command")])


def test_runs_program():
	calls: list[tuple[str, int]] = []

	def copy(source: str, count: int) -> str:
		calls.append((source, count))
		return "copied"

	program = Program(
		"copy",
		copy,
		arguments=[Argument("source")],
		options=[Option("count", type=int, default=1)],
	)

	assert_eq(program.run(["input.txt", "--count=2"]), "copied")
	assert_eq(calls, [("input.txt", 2)])


def test_runs_command():
	calls: list[tuple[str, object]] = []

	def copy(source: str) -> str:
		calls.append(("copy", source))
		return "copied"

	def show(verbose: bool) -> str:
		calls.append(("show", verbose))
		return "shown"

	program = Program(
		"files",
		commands=[
			Command("copy", copy, arguments=[Argument("source")]),
			Command("show", show, options=[Option("verbose", short="v", type=bool)]),
		],
	)

	assert_eq(program.run(["show", "-v"]), "shown")
	assert_eq(calls, [("show", True)])


def test_prints_help():
	calls: list[str] = []

	def copy(source: str) -> None:
		calls.append(source)

	program = Program(
		"copy",
		copy,
		description="Copy a file.",
		arguments=[Argument("source")],
	)
	stdout = StringIO()
	stderr = StringIO()

	with redirect_stdout(stdout), redirect_stderr(stderr):
		result = program.run(["--help"])

	assert_eq(result, None)
	assert_that(stdout.getvalue().startswith("usage: copy"))
	assert_that("Copy a file." in stdout.getvalue())
	assert_eq(stderr.getvalue(), "")
	assert_eq(calls, [])


def test_reports_parse_errors():
	calls: list[str] = []

	def copy(source: str) -> None:
		calls.append(source)

	program = Program(
		"files",
		commands=[Command("copy", copy, arguments=[Argument("source")])],
	)

	for argv, usage in [([], "usage: files"), (["copy"], "usage: files copy")]:
		stdout = StringIO()
		stderr = StringIO()
		with (
			redirect_stdout(stdout),
			redirect_stderr(stderr),
			assert_raises(SystemExit) as raised,
		):
			program.run(argv)

		exit = cast(SystemExit, raised.exception)
		assert_eq(exit.code, 2)
		assert_eq(stdout.getvalue(), "")
		assert_that(stderr.getvalue().startswith(usage))
		assert_that("files: error:" in stderr.getvalue())

	assert_eq(calls, [])


def test_prints_command_help():
	program = Program(
		"files",
		commands=[Command("copy", noop, description="Copy a file.")],
	)
	stdout = StringIO()
	stderr = StringIO()

	with redirect_stdout(stdout), redirect_stderr(stderr):
		result = program.run(["copy", "--help"])

	assert_eq(result, None)
	assert_that(stdout.getvalue().startswith("usage: files copy"))
	assert_that("Copy a file." in stdout.getvalue())
	assert_eq(stderr.getvalue(), "")
