from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
import sys
from typing import Any, cast

from luna.cli import Command, HelpRequested, ParseError, Program, argument, option
from luna.cli.parse import parse
from luna.test.assertion import assert_eq, assert_not, assert_raises, assert_that


class Apply(Command):
	"""Apply pending migrations."""

	name = "apply"
	target: str = argument(default="latest", help="migration to apply up to")
	dry: bool = option(default=False, short="d", help="report without applying")

	def run(self) -> object:
		return ("apply", self.target, self.dry)


class Status(Command):
	"""
	Report pending migrations.

	Lists each migration that has not been applied.
	"""

	name = "status"
	verbose: bool = option(default=False, short="v")

	def run(self) -> object:
		return ("status", self.verbose)


class Migrate(Program):
	"""Manage database migrations."""

	name = "migrate"
	commands = [Apply, Status]  # noqa: RUF012


class Backup(Program):
	"""Back up the database."""

	name = "backup"
	keep: int = option(default=7, short="k")

	def run(self) -> object:
		return ("backup", self.keep)


def declaration_error(declare: Any) -> str:
	with assert_raises(ValueError) as raised:
		declare()
	return str(raised.exception)


def parse_error(program: type[Program], argv: list[str]) -> ParseError:
	with assert_raises(ParseError) as raised:
		parse(program, argv)
	return cast(ParseError, raised.exception)


def help_for(program: type[Program], argv: list[str]) -> str:
	with assert_raises(HelpRequested) as raised:
		parse(program, argv)
	return cast(HelpRequested, raised.exception).help


def run_main(program: type[Program], argv: list[str]) -> tuple[object, str, str]:
	stdout = StringIO()
	stderr = StringIO()
	with redirect_stdout(stdout), redirect_stderr(stderr):
		result = program.main(argv)
	return result, stdout.getvalue(), stderr.getvalue()


def test_parses_direct_program():
	result = parse(Backup, ["-k", "3"])

	assert_that(result.program is Backup)
	assert_eq(result.command, None)
	assert_eq(result.values, {"keep": 3})


def test_selects_command():
	apply = parse(Migrate, ["apply", "v2", "-d"])
	status = parse(Migrate, ["status"])

	assert_that(apply.program is Migrate)
	assert_that(apply.command is Apply)
	assert_eq(apply.values, {"target": "v2", "dry": True})
	assert_that(status.command is Status)
	assert_eq(status.values, {"verbose": False})


def test_rejects_unknown_and_missing_commands():
	for argv in [[], ["unknown"], ["--", "apply"]]:
		error = parse_error(Migrate, argv)
		assert_that(error.usage.startswith("usage: migrate"))
		assert_not("migrate apply" in error.usage)


def test_accepts_only_help_before_command():
	assert_that(help_for(Migrate, ["--help", "apply"]).startswith("usage: migrate "))
	assert_that(help_for(Migrate, ["-h", "status"]).startswith("usage: migrate "))
	for argv in [["-v", "status"], ["--verbose", "status"], ["-d", "apply"]]:
		assert_that(parse_error(Migrate, argv).usage.startswith("usage: migrate "))


def test_reports_command_errors_with_command_usage():
	error = parse_error(Migrate, ["apply", "v2", "--dry=yes"])

	assert_that(error.usage.startswith("usage: migrate apply"))


def test_uses_program_and_command_names_verbatim():
	class ShowFile(Command):
		name = "show_file"

		def run(self):
			pass

	class Files(Program):
		name = "file-tool"
		commands = [ShowFile]  # noqa: RUF012

	assert_that(parse(Files, ["show_file"]).command is ShowFile)
	assert_that(parse_error(Files, ["show-file"]).usage.startswith("usage: file-tool"))
	assert_that(
		help_for(Files, ["show_file", "--help"]).startswith(
			"usage: file-tool show_file"
		)
	)


def test_describes_program_and_commands_in_help():
	program_help = help_for(Migrate, ["--help"])
	command_help = help_for(Migrate, ["apply", "--help"])

	for text in [
		"usage: migrate",
		"Manage database migrations.",
		"apply",
		"Apply pending migrations.",
		"status",
		"Report pending migrations.",
	]:
		assert_that(text in program_help)
	for text in [
		"usage: migrate apply",
		"Apply pending migrations.",
		"<target>",
		"migration to apply up to",
		"--dry, -d",
		"report without applying",
	]:
		assert_that(text in command_help)


def test_preserves_docstring_layout_in_help():
	help = help_for(Migrate, ["status", "--help"])

	assert_that(
		"Report pending migrations.\n\nLists each migration that has not been "
		"applied.\n" in help
	)


def test_omits_missing_descriptions():
	class Plain(Program):
		name = "plain"

		def run(self):
			pass

	assert_eq(
		help_for(Plain, ["--help"]),
		"usage: plain [--help]\n\n"
		"options:\n"
		"  --help, -h  show this help message and exit\n",
	)


def test_main_runs_direct_program():
	assert_eq(run_main(Backup, ["--keep", "3"]), (("backup", 3), "", ""))


def test_main_runs_selected_command():
	assert_eq(run_main(Migrate, ["apply", "-d"]), (("apply", "latest", True), "", ""))
	assert_eq(run_main(Migrate, ["status", "-v"]), (("status", True), "", ""))


def test_main_drops_program_path_from_argv():
	assert_eq(run_main(Backup, [sys.argv[0], "-k", "2"])[0], ("backup", 2))


def test_main_prints_help():
	for program, argv, usage in [
		(Backup, ["--help"], "usage: backup"),
		(Migrate, ["-h"], "usage: migrate"),
		(Migrate, ["apply", "--help"], "usage: migrate apply"),
	]:
		result, stdout, stderr = run_main(program, argv)

		assert_eq(result, None)
		assert_that(stdout.startswith(usage))
		assert_eq(stderr, "")


def test_main_reports_parse_errors():
	for program, argv, usage, message in [
		(Backup, ["--keep", "x"], "usage: backup", "backup: error: argument --keep"),
		(Migrate, [], "usage: migrate", "migrate: error: the following"),
		(
			Migrate,
			["apply", "-d=x"],
			"usage: migrate apply",
			"migrate: error: argument",
		),
	]:
		stdout = StringIO()
		stderr = StringIO()
		with (
			redirect_stdout(stdout),
			redirect_stderr(stderr),
			assert_raises(SystemExit) as raised,
		):
			program.main(argv)

		assert_eq(cast(SystemExit, raised.exception).code, 2)
		assert_eq(stdout.getvalue(), "")
		assert_that(stderr.getvalue().startswith(usage))
		assert_that(f"\n{message}" in stderr.getvalue())


def test_rejects_mixed_and_empty_programs():
	def with_values():
		class Mixed(Program):
			name = "mixed"
			commands = [Status]  # noqa: RUF012
			verbose: bool = option(default=False)

	def with_run():
		class Mixed(Program):
			name = "mixed"
			commands = [Status]  # noqa: RUF012

			def run(self):
				pass

	def empty():
		class Empty(Program):
			name = "empty"

	def values_without_run():
		class Empty(Program):
			name = "empty"
			verbose: bool = option(default=False)

	def no_commands():
		class Empty(Program):
			name = "empty"
			commands = []  # noqa: RUF012

	for declare in [with_values, with_run]:
		assert_eq(
			declaration_error(declare),
			"Mixed cannot declare both commands and values or run()",
		)
	for declare in [empty, values_without_run]:
		assert_eq(
			declaration_error(declare),
			"Empty must declare commands or override run()",
		)
	assert_eq(
		declaration_error(no_commands),
		"Empty.commands must list at least one command",
	)


def test_rejects_invalid_commands():
	def not_a_command():
		class Tools(Program):
			name = "tools"
			commands = [Status, Backup]  # noqa: RUF012

	def duplicate():
		class Again(Command):
			name = "status"

			def run(self):
				pass

		class Tools(Program):
			name = "tools"
			commands = [Status, Again]  # noqa: RUF012

	assert_that(
		declaration_error(not_a_command).startswith(
			"Tools.commands contains a non-Command entry"
		)
	)
	assert_eq(
		declaration_error(duplicate),
		"Tools.commands has duplicate name: 'status'",
	)


def test_requires_direct_inheritance():
	class Mixin:
		pass

	def from_program():
		class Extended(Backup):
			name = "extended"

	def with_mixin():
		class Extended(Program, Mixin):
			name = "extended"

			def run(self):
				pass

	for declare in [from_program, with_mixin]:
		assert_eq(
			declaration_error(declare),
			"Extended must inherit only from Program",
		)
