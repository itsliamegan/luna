from __future__ import annotations

import argparse
from dataclasses import dataclass
from typing import Never, TYPE_CHECKING

from luna.cli.conversion import escape
from luna.cli.runnable import Runnable, description

if TYPE_CHECKING:
	from luna.cli.command import Command
	from luna.cli.program import Program

COMMAND_DESTINATION = "__command"


@dataclass
class ParseResult:
	program: type[Program]
	command: type[Command] | None
	values: dict[str, object]


class ParseError(Exception):
	def __init__(self, message: str, usage: str):
		super().__init__(message)
		self.message = message
		self.usage = usage


class HelpRequested(Exception):
	def __init__(self, help: str):
		super().__init__(help)
		self.help = help


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
		value.add_to(parser)


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
	return {name: value.parsed(namespace) for name, value in runnable.settled().items()}
