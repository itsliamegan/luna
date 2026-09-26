import argparse
from copy import copy
from typing import Any

from luna.cli.conversion import (
	Conversion,
	check_default,
	converter,
	help_text,
	scalar,
)
from luna.declarative import Declaration, DeclarationError, MISSING, split_nullable


class Argument:
	name: str
	declaration: Declaration[Conversion]

	def __init__(self, default: object = MISSING, help: str | None = None):
		self.default = default
		self.help = help

	def bind(self, declaration: Declaration[Conversion]):
		self.name = declaration.name
		self.declaration = declaration

	def settle(self, declaration: Declaration[Conversion]) -> Conversion:
		value_type, nullable = split_nullable(declaration.name, declaration.annotation)
		if not scalar(value_type):
			raise DeclarationError(
				declaration.name,
				f"unsupported argument type: {declaration.annotation!r}",
			)

		conversion = Conversion(value_type, nullable)
		check_default(declaration, conversion, self.default)
		return conversion

	@property
	def type(self) -> Any:
		return self.declaration.resolve().type

	@property
	def required(self) -> bool:
		return self.default is MISSING

	@property
	def initial(self) -> object:
		return copy(self.default)

	def add_to(self, parser: argparse.ArgumentParser):
		if self.required:
			parser.add_argument(
				self.name,
				type=converter(self.type),
				metavar=f"<{self.name}>",
				help=help_text(self.help, self.type),
			)
		else:
			parser.add_argument(
				self.name,
				type=converter(self.type),
				nargs="?",
				default=self.initial,
				metavar=f"<{self.name}>",
				help=help_text(self.help, self.type),
			)

	def parsed(self, namespace: argparse.Namespace) -> object:
		return getattr(namespace, self.name)


def argument(*, default: object = MISSING, help: str | None = None) -> Any:
	return Argument(default, help)
