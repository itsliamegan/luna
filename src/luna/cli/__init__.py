from collections.abc import Callable
from dataclasses import dataclass
import sys

COMMAND_DESTINATION = "__command"

type Action = Callable[..., object]


@dataclass
class Argument:
	name: str
	type: type = str
	required: bool = True
	default: object | None = None
	help: str | None = None


@dataclass
class Option:
	name: str
	short: str | None = None
	type: type = str
	required: bool = False
	default: object | None = None
	help: str | None = None


@dataclass(init=False)
class Command:
	name: str
	action: Action
	description: str | None
	arguments: list[Argument]
	options: list[Option]

	def __init__(
		self,
		name: str,
		action: Action,
		description: str | None = None,
		arguments: list[Argument] | None = None,
		options: list[Option] | None = None,
	):
		self.name = name
		self.action = action
		self.description = description
		self.arguments = [] if arguments is None else arguments
		self.options = [] if options is None else options
		validate_value_names(self.arguments, self.options, {COMMAND_DESTINATION})


@dataclass(init=False)
class Program:
	name: str
	action: Action | None
	description: str | None
	arguments: list[Argument]
	options: list[Option]
	commands: list[Command]

	def __init__(
		self,
		name: str,
		action: Action | None = None,
		description: str | None = None,
		arguments: list[Argument] | None = None,
		options: list[Option] | None = None,
		commands: list[Command] | None = None,
	):
		self.name = name
		self.action = action
		self.description = description
		self.arguments = [] if arguments is None else arguments
		self.options = [] if options is None else options
		self.commands = [] if commands is None else commands

		if self.commands and (self.arguments or self.options):
			raise ValueError(
				"a program cannot contain both commands and direct arguments"
			)
		if self.action is None and not self.commands:
			raise ValueError("a program must define either an action or commands")

		if self.commands:
			for command in self.commands:
				validate_value_names(
					command.arguments,
					command.options,
					{COMMAND_DESTINATION},
				)
		else:
			validate_value_names(self.arguments, self.options)

	def run(self, argv: list[str]) -> object:
		from luna.cli.parse import HelpRequested, ParseError, parse

		try:
			result = parse(self, argv)
		except HelpRequested as requested:
			print(requested.help, end="")
			return None
		except ParseError as error:
			print(error.usage, end="", file=sys.stderr)
			print(f"{self.name}: error: {error.message}", file=sys.stderr)
			raise SystemExit(2) from None

		if result.command is not None:
			action = result.command.action
		elif self.action is not None:
			action = self.action
		return action(**result.values)


def validate_value_names(
	arguments: list[Argument],
	options: list[Option],
	reserved: set[str] | None = None,
):
	names = set() if reserved is None else set(reserved)
	for declaration in [*arguments, *options]:
		if declaration.name in names:
			raise ValueError(f"duplicate or reserved value name: {declaration.name!r}")
		names.add(declaration.name)
