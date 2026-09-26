import argparse
from copy import copy
from typing import Any, get_args, get_origin

from luna.cli.conversion import (
	Conversion,
	check_default,
	converter,
	help_text,
	scalar,
)
from luna.declarative import Declaration, DeclarationError, MISSING, split_nullable


class Option:
	name: str
	declaration: Declaration[Conversion]

	def __init__(
		self,
		default: object = MISSING,
		short: str | None = None,
		help: str | None = None,
	):
		self.default = default
		self.short = short
		self.help = help

	def bind(self, declaration: Declaration[Conversion]):
		self.name = declaration.name
		self.declaration = declaration

	def settle(self, declaration: Declaration[Conversion]) -> Conversion:
		value_type, nullable = split_nullable(declaration.name, declaration.annotation)
		if not accepts(value_type, nullable):
			raise DeclarationError(
				declaration.name,
				f"unsupported option type: {declaration.annotation!r}",
			)

		conversion = Conversion(value_type, nullable)
		check_default(declaration, conversion, self.default)
		return conversion

	@property
	def type(self) -> Any:
		return self.declaration.resolve().type

	@property
	def flag(self) -> bool:
		return self.type is bool

	@property
	def repeated(self) -> bool:
		return get_origin(self.type) is list

	@property
	def item_type(self) -> Any:
		if self.repeated:
			return get_args(self.type)[0]
		return self.type

	@property
	def required(self) -> bool:
		return self.default is MISSING and not self.flag and not self.repeated

	@property
	def initial(self) -> object:
		if self.default is not MISSING:
			return copy(self.default)
		if self.flag:
			return False
		if self.repeated:
			return []
		return MISSING

	def add_to(self, parser: argparse.ArgumentParser):
		option_strings = [f"--{self.name}"]
		if self.short is not None:
			option_strings.append(f"-{self.short}")

		if self.flag:
			parser.add_argument(
				*option_strings,
				dest=self.name,
				action="store_true",
				default=self.initial,
				help=help_text(self.help, self.type),
			)
		elif self.repeated:
			parser.add_argument(
				*option_strings,
				dest=self.name,
				action="append",
				type=converter(self.item_type),
				default=None,
				metavar=f"<{self.name}>",
				help=help_text(self.help, self.item_type),
			)
		else:
			parser.add_argument(
				*option_strings,
				dest=self.name,
				type=converter(self.type),
				required=self.required,
				default=None if self.required else self.initial,
				metavar=f"<{self.name}>",
				help=help_text(self.help, self.type),
			)

	def parsed(self, namespace: argparse.Namespace) -> object:
		value = getattr(namespace, self.name)
		# Supplied list values replace the default rather than extending it.
		if self.repeated and value is None:
			return self.initial
		return value


def option(
	*,
	default: object = MISSING,
	short: str | None = None,
	help: str | None = None,
) -> Any:
	return Option(default, short, help)


def accepts(value_type: object, nullable: bool) -> bool:
	if scalar(value_type):
		return True
	if nullable:
		return False
	if value_type is bool:
		return True

	arguments = get_args(value_type)
	return (
		get_origin(value_type) is list and len(arguments) == 1 and scalar(arguments[0])
	)
