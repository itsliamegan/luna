from __future__ import annotations

import argparse
from dataclasses import dataclass
from typing import Never, cast, get_args, get_origin

from luna.cli import Argument, Command, Option, Program

COMMAND_DESTINATION = "__command"


@dataclass(frozen=True)
class ParseResult:
	program: Program
	command: Command | None
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


def parse(program: Program, argv: list[str]) -> ParseResult:
	if program.commands:
		return parse_commands(program, argv)
	else:
		return parse_program(program, argv)


def create_parser(name: str, description: str | None) -> ArgumentParser:
	parser = ArgumentParser(
		prog=name,
		description=description,
		add_help=False,
	)
	add_help(parser)
	return parser


def add_commands(parser: ArgumentParser, commands: list[Command]) -> str:
	subparsers = parser.add_subparsers(
		dest=COMMAND_DESTINATION,
		required=True,
		metavar="<command>",
	)
	for command in commands:
		command_parser = subparsers.add_parser(
			command.name,
			description=command.description,
			help=command.description,
			add_help=False,
		)
		add_help(command_parser)
		add_arguments_and_options(
			command_parser,
			command.arguments,
			command.options,
		)
	return COMMAND_DESTINATION


def add_help(parser: argparse.ArgumentParser):
	parser.add_argument(
		"--help",
		"-h",
		action=HelpAction,
		help="show this help message and exit",
	)


def add_arguments_and_options(
	parser: argparse.ArgumentParser,
	arguments: list[Argument],
	options: list[Option],
):
	for argument in arguments:
		add_argument(parser, argument)
	for option in options:
		add_option(parser, option)


def add_argument(parser: argparse.ArgumentParser, argument: Argument):
	if argument.required:
		parser.add_argument(
			argument.name,
			type=argument.type,
			metavar=f"<{argument.name}>",
			help=argument.help,
		)
	else:
		parser.add_argument(
			argument.name,
			type=argument.type,
			nargs="?",
			default=argument.default,
			metavar=f"<{argument.name}>",
			help=argument.help,
		)


def add_option(parser: argparse.ArgumentParser, option: Option):
	option_strings = [f"--{option.name}"]
	if option.short is not None:
		option_strings.append(f"-{option.short}")

	if option.type is bool:
		parser.add_argument(
			*option_strings,
			dest=option.name,
			action="store_true",
			required=option.required,
			default=option.default if option.default is not None else False,
			help=option.help,
		)
	elif get_origin(option.type) is list:
		parser.add_argument(
			*option_strings,
			dest=option.name,
			action="append",
			type=get_args(option.type)[0],
			required=option.required,
			default=None,
			metavar=f"<{option.name}>",
			help=option.help,
		)
	else:
		parser.add_argument(
			*option_strings,
			dest=option.name,
			type=option.type,
			required=option.required,
			default=option.default,
			metavar=f"<{option.name}>",
			help=option.help,
		)


def parse_program(program: Program, argv: list[str]) -> ParseResult:
	parser = create_parser(program.name, program.description)
	add_arguments_and_options(parser, program.arguments, program.options)
	namespace = parser.parse_args(argv)
	values = parse_values(namespace, program.arguments, program.options)
	return ParseResult(program, None, values)


def parse_commands(program: Program, argv: list[str]) -> ParseResult:
	parser = create_parser(program.name, program.description)
	destination = add_commands(parser, program.commands)

	if argv and argv[0] == "--":
		parser.error("argument command: invalid choice: '--'")

	namespace = parser.parse_args(argv)
	command_name = getattr(namespace, destination)
	command = next(
		command for command in program.commands if command.name == command_name
	)
	values = parse_values(namespace, command.arguments, command.options)
	return ParseResult(program, command, values)


def parse_values(
	namespace: argparse.Namespace,
	arguments: list[Argument],
	options: list[Option],
) -> dict[str, object]:
	parsed = vars(namespace)
	values = {argument.name: parsed[argument.name] for argument in arguments}
	for option in options:
		value = parsed[option.name]
		if get_origin(option.type) is list and value is None:
			default = cast(list[object] | None, option.default)
			value = [] if default is None else list(default)
		values[option.name] = value
	return values
