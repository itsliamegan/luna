from contextlib import redirect_stderr, redirect_stdout
from enum import StrEnum
from io import StringIO
from typing import Any, cast

from luna.cli import Command, Program, argument, option
from luna.test.assertion import assert_eq, assert_raises, assert_that


class Mode(StrEnum):
	SAFE = "safe"
	FAST = "fast"


class Apply(Command):
	"""Apply pending migrations."""

	name = "apply"
	target: str = argument("latest")
	dry: bool = option(short="d")
	steps: list[int] = option()

	def run(self) -> object:
		return ("apply", self.target, self.dry, self.steps)


class Status(Command):
	"""Report pending migrations."""

	name = "status"

	def run(self) -> object:
		return "status"


class Migrate(Program):
	name = "migrate"
	commands = [Apply, Status]  # noqa: RUF012


class Backup(Program):
	"""Back up the database."""

	name = "backup"
	dry: bool = option(short="d")
	keep: int = option(7, short="k")

	def run(self) -> object:
		return ("backup", self.dry, self.keep)


def declaration_error(declare: Any) -> str:
	with assert_raises(ValueError) as raised:
		declare()
	return str(raised.exception)


def run_main(program: type[Program], argv: list[str]) -> tuple[object, str, str]:
	stdout = StringIO()
	stderr = StringIO()
	with redirect_stdout(stdout), redirect_stderr(stderr):
		result = program.main(argv)
	return result, stdout.getvalue(), stderr.getvalue()


def test_constructs_without_argv():
	apply = Apply(dry=True, steps=[3])

	assert_eq(apply.run(), ("apply", "latest", True, [3]))
	assert_eq(Backup(keep=3).run(), ("backup", False, 3))  # ty: ignore[missing-argument]


def test_copies_defaults_for_each_instance():
	first = Apply()  # ty: ignore[missing-argument]
	first.steps.append(1)

	assert_eq(Apply().steps, [])  # ty: ignore[missing-argument]


def test_rejects_unexpected_and_missing_values():
	class Greet(Command):
		name = "greet"
		person: str = argument()

		def run(self):
			pass

	with assert_raises(TypeError) as missing:
		Greet()  # ty: ignore[missing-argument]
	with assert_raises(TypeError) as unexpected:
		Greet(person="Ada", loud=True)  # ty: ignore[unknown-argument]

	assert_eq(str(missing.exception), "Greet is missing values: person")
	assert_eq(str(unexpected.exception), "Greet got unexpected values: loud")


def test_requires_run_on_commands():
	class Idle(Command):
		name = "idle"

	with assert_raises(TypeError):
		Idle()


def test_runs_direct_program():
	assert_eq(run_main(Backup, ["-d", "--keep", "3"]), (("backup", True, 3), "", ""))


def test_runs_selected_command():
	assert_eq(
		run_main(Migrate, ["apply", "v2", "--steps=1", "--steps=2"]),
		(("apply", "v2", False, [1, 2]), "", ""),
	)
	assert_eq(run_main(Migrate, ["status"]), ("status", "", ""))


def test_drops_program_path_from_argv():
	import sys

	assert_eq(run_main(Backup, [sys.argv[0], "-k", "2"])[0], ("backup", False, 2))


def test_prints_help():
	result, stdout, stderr = run_main(Backup, ["--help"])

	assert_eq(result, None)
	assert_that(stdout.startswith("usage: backup"))
	assert_that("Back up the database." in stdout)
	assert_eq(stderr, "")


def test_prints_command_help():
	result, stdout, stderr = run_main(Migrate, ["apply", "--help"])

	assert_eq(result, None)
	assert_that(stdout.startswith("usage: migrate apply"))
	assert_that("Apply pending migrations." in stdout)
	assert_eq(stderr, "")


def test_reports_parse_errors():
	for argv, usage in [
		([], "usage: migrate"),
		(["apply", "--steps", "x"], "usage: migrate apply"),
	]:
		with assert_raises(SystemExit) as raised:
			run_main(Migrate, argv)

		assert_eq(cast(SystemExit, raised.exception).code, 2)

	stdout = StringIO()
	stderr = StringIO()
	with redirect_stdout(stdout), redirect_stderr(stderr), assert_raises(SystemExit):
		Migrate.main(["apply", "--steps", "x"])

	assert_eq(stdout.getvalue(), "")
	assert_that(stderr.getvalue().startswith("usage: migrate apply"))
	assert_that("\nmigrate: error: argument --steps" in stderr.getvalue())


def test_rejects_mixed_and_empty_programs():
	def with_values():
		class Mixed(Program):
			name = "mixed"
			commands = [Status]  # noqa: RUF012
			verbose: bool = option()

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
			verbose: bool = option()

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

	def from_command():
		class Extended(Status):
			name = "extended"

	def from_program():
		class Extended(Backup):
			name = "extended"

	def with_mixin():
		class Extended(Command, Mixin):
			name = "extended"

	assert_eq(
		declaration_error(from_command), "Extended must inherit only from Command"
	)
	assert_eq(
		declaration_error(from_program), "Extended must inherit only from Program"
	)
	assert_eq(declaration_error(with_mixin), "Extended must inherit only from Command")


def test_validates_names():
	def missing():
		class Unnamed(Command):
			pass

	def empty():
		class Unnamed(Command):
			name = ""

	def not_a_string():
		class Unnamed(Command):
			name = 1

	def dashed():
		class Unnamed(Command):
			name = "-apply"

	for declare in [missing, empty, not_a_string]:
		assert_eq(
			declaration_error(declare),
			"Unnamed must set name to a nonempty string",
		)
	assert_eq(
		declaration_error(dashed),
		"Unnamed.name must not begin with '-': '-apply'",
	)


def test_rejects_reserved_names():
	def named(value: str):
		def declare():
			type(
				"Reserved",
				(Command,),
				{"__annotations__": {value: bool}, "name": "reserved"},
			)

		return declare

	for value in ["run", "main", "name", "commands", "help", "declared", "settled"]:
		assert_eq(
			declaration_error(named(value)),
			f"Reserved.{value}: name is reserved",
		)

	def short_help():
		class Reserved(Command):
			name = "reserved"
			hidden: bool = option(short="h")

	assert_eq(
		declaration_error(short_help),
		"Reserved.hidden: short alias is reserved: 'h'",
	)


def test_validates_short_aliases():
	def duplicate():
		class Aliases(Command):
			name = "aliases"
			verbose: bool = option(short="v")
			version: bool = option(short="v")

	def long():
		class Aliases(Command):
			name = "aliases"
			verbose: bool = option(short="vv")

	def not_a_letter():
		class Aliases(Command):
			name = "aliases"
			verbose: bool = option(short="1")

	assert_eq(
		declaration_error(duplicate),
		"Aliases.version: duplicate short alias: 'v'",
	)
	assert_eq(
		declaration_error(long),
		"Aliases.verbose: short alias must be a single ASCII letter: 'vv'",
	)
	assert_eq(
		declaration_error(not_a_letter),
		"Aliases.verbose: short alias must be a single ASCII letter: '1'",
	)


def test_requires_required_arguments_first():
	def declare():
		class Order(Command):
			name = "order"
			first: str = argument("x")
			second: str = argument()

	assert_eq(
		declaration_error(declare),
		"Order.second: required argument follows optional argument first",
	)


def test_accepts_supported_types():
	class Supported(Command):
		name = "supported"
		text: str = argument()
		number: int = argument()
		mode: Mode = argument()
		maybe_text: str | None = argument(None)
		maybe_number: int | None = argument(None)
		maybe_mode: Mode | None = argument(None)
		flag: bool = option()
		texts: list[str] = option()
		numbers: list[int] = option()
		modes: list[Mode] = option()

		def run(self):
			pass

	supported = Supported(
		text="a",
		number=1,
		mode=Mode.FAST,
		flag=True,
		texts=["b"],
		numbers=[2],
		modes=[Mode.SAFE],
	)

	assert_eq(supported.maybe_mode, None)
	assert_eq(supported.modes, [Mode.SAFE])


def test_rejects_unsupported_types():
	def declare(annotation: object, specifier: object):
		def create():
			type(
				"Typed",
				(Command,),
				{
					"__annotations__": {"value": annotation},
					"value": specifier,
					"name": "typed",
				},
			)

		return create

	for annotation, specifier, kind in [
		(float, option(), "option"),
		(bool, argument(), "argument"),
		(list[str], argument(), "argument"),
		(bool | None, option(), "option"),
		(list[str] | None, option(), "option"),
		(list[float], option(), "option"),
		(list[list[str]], option(), "option"),
	]:
		assert_that(
			declaration_error(declare(annotation, specifier)).startswith(
				f"Typed.value: unsupported {kind} type:"
			)
		)
	assert_eq(
		declaration_error(declare(str | int, option())),
		"Typed.value: unsupported type: str | int",
	)


def test_rejects_mismatched_defaults():
	def declare(annotation: object, default: object):
		def create():
			type(
				"Defaults",
				(Command,),
				{
					"__annotations__": {"value": annotation},
					"value": option(default),
					"name": "defaults",
				},
			)

		return create

	assert_eq(
		declaration_error(declare(int, None)),
		"Defaults.value: default None requires a nullable type: <class 'int'>",
	)
	for annotation, default in [
		(int, True),
		(int, "1"),
		(str, 1),
		(bool, 0),
		(Mode, "safe"),
		(list[int], [True]),
		(list[str], ("a",)),
		(int | None, "1"),
	]:
		assert_that(
			declaration_error(declare(annotation, default)).startswith(
				f"Defaults.value: default {default!r} does not match type"
			)
		)


def test_resolves_forward_references_before_use():
	class Later(Command):
		name = "later"
		mode: Pending = option(help="a mode declared later")

		def run(self):
			return self.mode

	class Pending(StrEnum):
		ON = "on"

	assert_eq(Later(mode=Pending.ON).run(), Pending.ON)
