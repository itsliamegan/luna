import argparse
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Never

from luna.cli import (
	Command,
	HelpRequested,
	Kind,
	ParseError,
	Program,
	Runnable,
	Value,
	description,
)

COMMAND_DESTINATION = "__command"


@dataclass
class ParseResult:
	program: type[Program]
	command: type[Command] | None
	values: dict[str, object]


class ArgumentParser(argparse.ArgumentParser):
	def error(self, message: str) -> Never:
		raise ParseError(message, self.format_usage())


class HelpAction(argparse.Action):
	def __init__(
		self,
		option_strings: list[str],
		dest: str = argparse.SUPPRESS,
		default: object = argparse.SUPPRESS,
		help: str | None = None,
	):
		super().__init__(
			option_strings=option_strings,
			dest=dest,
			nargs=0,
			default=default,
			help=help,
		)

	def __call__(
		self,
		parser: argparse.ArgumentParser,
		namespace: argparse.Namespace,
		values: object,
		option_string: str | None = None,
	):
		raise HelpRequested(parser.format_help())


def parse(program: type[Program], argv: list[str]) -> ParseResult:
	if program.commands:
		return parse_commands(program, argv)
	else:
		return parse_program(program, argv)


def create_parser(runnable: type[Runnable]) -> ArgumentParser:
	parser = ArgumentParser(
		prog=runnable.name,
		description=description(runnable),
		formatter_class=argparse.RawDescriptionHelpFormatter,
		add_help=False,
		color=False,
	)
	add_help(parser)
	return parser


def add_commands(parser: ArgumentParser, commands: list[type[Command]]):
	subparsers = parser.add_subparsers(
		dest=COMMAND_DESTINATION,
		required=True,
		metavar="<command>",
	)
	for command in commands:
		command_parser = subparsers.add_parser(
			command.name,
			description=description(command),
			help=escape(description(command)),
			formatter_class=argparse.RawDescriptionHelpFormatter,
			add_help=False,
		)
		add_help(command_parser)
		add_values(command_parser, command)


def add_help(parser: argparse.ArgumentParser):
	parser.add_argument(
		"--help",
		"-h",
		action=HelpAction,
		help="show this help message and exit",
	)


def add_values(parser: argparse.ArgumentParser, runnable: type[Runnable]):
	parser._positionals.title = "arguments"
	for value in runnable.settled().values():
		if value.kind is Kind.ARGUMENT:
			add_argument(parser, value)
		else:
			add_option(parser, value)


def add_argument(parser: argparse.ArgumentParser, value: Value):
	if value.required:
		parser.add_argument(
			value.name,
			type=converter(value.type),
			metavar=f"<{value.name}>",
			help=help_text(value),
		)
	else:
		parser.add_argument(
			value.name,
			type=converter(value.type),
			nargs="?",
			default=value.initial,
			metavar=f"<{value.name}>",
			help=help_text(value),
		)


def add_option(parser: argparse.ArgumentParser, value: Value):
	option_strings = [f"--{value.name}"]
	if value.short is not None:
		option_strings.append(f"-{value.short}")

	if value.flag:
		parser.add_argument(
			*option_strings,
			dest=value.name,
			action="store_true",
			default=value.initial,
			help=help_text(value),
		)
	elif value.repeated:
		parser.add_argument(
			*option_strings,
			dest=value.name,
			action="append",
			type=converter(value.item_type),
			default=None,
			metavar=f"<{value.name}>",
			help=help_text(value),
		)
	else:
		parser.add_argument(
			*option_strings,
			dest=value.name,
			type=converter(value.type),
			required=value.required,
			default=None if value.required else value.initial,
			metavar=f"<{value.name}>",
			help=help_text(value),
		)


def converter(kind: Any) -> Callable[[str], object]:
	if isinstance(kind, type) and issubclass(kind, StrEnum):
		return choice_converter(kind)
	return kind


def choice_converter(choices: type[StrEnum]) -> Callable[[str], object]:
	def convert(text: str) -> StrEnum:
		try:
			return choices(text)
		except ValueError:
			raise argparse.ArgumentTypeError(
				f"invalid choice: {text!r} (choose from {listing(choices)})"
			) from None

	return convert


def help_text(value: Value) -> str | None:
	help = escape(value.help)
	item_type = value.item_type
	if not (isinstance(item_type, type) and issubclass(item_type, StrEnum)):
		return help

	choices = f"choices: {listing(item_type)}"
	if help is None:
		return choices
	return f"{help} ({choices})"


def listing(choices: type[StrEnum]) -> str:
	return ", ".join(member.value for member in choices)


def escape(help: str | None) -> str | None:
	if help is None:
		return None
	return help.replace("%", "%%")


def parse_program(program: type[Program], argv: list[str]) -> ParseResult:
	parser = create_parser(program)
	add_values(parser, program)
	namespace = parser.parse_args(argv)
	return ParseResult(program, None, parse_values(namespace, program))


def parse_commands(program: type[Program], argv: list[str]) -> ParseResult:
	parser = create_parser(program)
	add_commands(parser, program.commands)

	if argv and argv[0] == "--":
		parser.error("argument command: invalid choice: '--'")

	namespace = parser.parse_args(argv)
	command_name = getattr(namespace, COMMAND_DESTINATION)
	command = next(
		command for command in program.commands if command.name == command_name
	)
	return ParseResult(program, command, parse_values(namespace, command))


def parse_values(
	namespace: argparse.Namespace,
	runnable: type[Runnable],
) -> dict[str, object]:
	parsed = vars(namespace)
	values = {}
	for value in runnable.settled().values():
		parsed_value = parsed[value.name]
		if value.repeated and parsed_value is None:
			parsed_value = value.initial
		values[value.name] = parsed_value
	return values
