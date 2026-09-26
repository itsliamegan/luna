import argparse
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, get_args, get_origin

from luna.declarative import Declaration, DeclarationError, MISSING


@dataclass
class Conversion:
	type: Any
	nullable: bool


def scalar(annotation: object) -> bool:
	return annotation is str or annotation is int or choices(annotation)


def choices(annotation: object) -> bool:
	return isinstance(annotation, type) and issubclass(annotation, StrEnum)


def check_default(
	declaration: Declaration[Conversion],
	conversion: Conversion,
	default: object,
):
	if default is MISSING:
		return
	if default is None:
		if conversion.nullable:
			return
		raise DeclarationError(
			declaration.name,
			f"default None requires a nullable type: {declaration.annotation!r}",
		)
	if not matches(conversion.type, default):
		raise DeclarationError(
			declaration.name,
			f"default {default!r} does not match type {declaration.annotation!r}",
		)


def matches(annotation: Any, default: object) -> bool:
	if get_origin(annotation) is list:
		(item_type,) = get_args(annotation)
		return type(default) is list and all(
			type(item) is item_type for item in default
		)
	return type(default) is annotation


def converter(value_type: Any) -> Callable[[str], object]:
	if not choices(value_type):
		return value_type

	def convert(text: str) -> StrEnum:
		try:
			return value_type(text)
		except ValueError:
			raise argparse.ArgumentTypeError(
				f"invalid choice: {text!r} (choose from {listing(value_type)})"
			) from None

	return convert


def help_text(help: str | None, value_type: Any) -> str | None:
	help = escape(help)
	if not choices(value_type):
		return help

	listed = f"choices: {listing(value_type)}"
	if help is None:
		return listed
	return f"{help} ({listed})"


def listing(value_type: type[StrEnum]) -> str:
	return ", ".join(member.value for member in value_type)


def escape(help: str | None) -> str | None:
	if help is None:
		return None
	return help.replace("%", "%%")
