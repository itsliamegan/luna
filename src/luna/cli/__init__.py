from abc import ABC, abstractmethod
from copy import copy
from dataclasses import dataclass
from enum import Enum, StrEnum
import inspect
import string
import sys
from typing import Any, ClassVar, dataclass_transform, get_args, get_origin

from luna.declarative import (
	Declaration,
	DeclarationError,
	MISSING,
	check_init_keywords,
	check_single_base,
	declarations,
	split_nullable,
)

RESERVED_NAMES = {"run", "main", "name", "commands", "help"}
RESERVED_SHORTS = {"h"}


class ParseError(Exception):
	def __init__(self, message: str, usage: str):
		super().__init__(message)
		self.message = message
		self.usage = usage


class HelpRequested(Exception):
	def __init__(self, help: str):
		super().__init__(help)
		self.help = help


class Kind(Enum):
	ARGUMENT = "argument"
	OPTION = "option"


@dataclass
class Specifier:
	kind: Kind
	default: object = MISSING
	short: str | None = None
	help: str | None = None


def argument(
	*,
	default: object = MISSING,
	help: str | None = None,
) -> Any:
	return Specifier(Kind.ARGUMENT, default, None, help)


def option(
	*,
	default: object = MISSING,
	short: str | None = None,
	help: str | None = None,
) -> Any:
	return Specifier(Kind.OPTION, default, short, help)


@dataclass
class Value:
	name: str
	kind: Kind
	type: Any
	nullable: bool
	default: object
	short: str | None
	help: str | None

	@property
	def required(self) -> bool:
		return self.default is MISSING

	@property
	def initial(self) -> object:
		return copy(self.default)

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


def specify(declaration: Declaration[Value]) -> Specifier:
	if isinstance(declaration.default, Specifier):
		return declaration.default
	return Specifier(Kind.OPTION, declaration.default)


def settle(declaration: Declaration[Value]) -> Value:
	name = declaration.name
	specifier = specify(declaration)
	check_value(name, specifier)

	annotation, nullable = split_nullable(name, declaration.annotation)
	if not accepts(specifier.kind, annotation, nullable):
		raise DeclarationError(
			name,
			f"unsupported {specifier.kind.value} type: {declaration.annotation!r}",
		)

	default = specifier.default
	if default is MISSING:
		if annotation is bool:
			default = False
		elif get_origin(annotation) is list:
			default = []
	elif default is None:
		if not nullable:
			raise DeclarationError(
				name,
				f"default None requires a nullable type: {declaration.annotation!r}",
			)
	elif not matches(annotation, default):
		raise DeclarationError(
			name,
			f"default {default!r} does not match type {declaration.annotation!r}",
		)

	return Value(
		name,
		specifier.kind,
		annotation,
		nullable,
		default,
		specifier.short,
		specifier.help,
	)


def check_value(name: str, specifier: Specifier):
	reserved = (
		RESERVED_NAMES | set(vars(Runnable)) | set(vars(Program)) | set(vars(Command))
	)
	if name in reserved:
		raise DeclarationError(name, "name is reserved")

	short = specifier.short
	if short is None:
		return
	if len(short) != 1 or short not in string.ascii_letters:
		raise DeclarationError(
			name,
			f"short alias must be a single ASCII letter: {short!r}",
		)
	if short in RESERVED_SHORTS:
		raise DeclarationError(name, f"short alias is reserved: {short!r}")


def scalar(annotation: object) -> bool:
	return (
		annotation is str
		or annotation is int
		or (isinstance(annotation, type) and issubclass(annotation, StrEnum))
	)


def accepts(kind: Kind, annotation: object, nullable: bool) -> bool:
	if scalar(annotation):
		return True
	if kind is Kind.ARGUMENT or nullable:
		return False
	if annotation is bool:
		return True

	arguments = get_args(annotation)
	return (
		get_origin(annotation) is list and len(arguments) == 1 and scalar(arguments[0])
	)


def matches(annotation: Any, default: object) -> bool:
	if get_origin(annotation) is list:
		(item_type,) = get_args(annotation)
		return type(default) is list and all(
			type(item) is item_type for item in default
		)
	return type(default) is annotation


def description(owner: type) -> str | None:
	docstring = vars(owner).get("__doc__")
	if docstring is None:
		return None
	return inspect.cleandoc(docstring)


@dataclass_transform(
	kw_only_default=True,
	eq_default=False,
	field_specifiers=(argument, option),
)
class Runnable(ABC):
	name: ClassVar[str]
	declared: ClassVar[dict[str, Declaration[Value]]] = {}

	def __init__(self, **values: Any):
		owner = type(self)
		settled = owner.settled()
		check_init_keywords(
			owner,
			"values",
			values,
			settled,
			[name for name, value in settled.items() if value.required],
		)
		for name, value in settled.items():
			setattr(self, name, values.get(name, value.initial))

	@classmethod
	def declare(cls):
		check_name(cls)
		declared = {}
		shorts = set()
		optional_argument = None
		for declaration in declarations(cls, settle, ValueError):
			name = declaration.name
			specifier = specify(declaration)
			if specifier.kind is Kind.ARGUMENT:
				if specifier.default is not MISSING:
					optional_argument = name
				elif optional_argument is not None:
					raise ValueError(
						f"{cls.__name__}.{name}: required argument follows "
						f"optional argument {optional_argument}"
					)

			if specifier.short is not None:
				if specifier.short in shorts:
					raise ValueError(
						f"{cls.__name__}.{name}: duplicate short alias: "
						f"{specifier.short!r}"
					)
				shorts.add(specifier.short)

			declared[name] = declaration
		cls.declared = declared

	@classmethod
	def settled(cls) -> dict[str, Value]:
		return {
			name: declaration.resolve() for name, declaration in cls.declared.items()
		}

	@abstractmethod
	def run(self) -> object: ...


class Command(Runnable):
	def __init_subclass__(cls, **keywords: Any):
		super().__init_subclass__(**keywords)
		check_single_base(cls, Command, ValueError)
		cls.declare()


class Program(Runnable):
	commands: ClassVar[list[type[Command]]] = []

	def __init_subclass__(cls, **keywords: Any):
		super().__init_subclass__(**keywords)
		check_single_base(cls, Program, ValueError)
		cls.declare()

		direct = "run" in vars(cls)
		if "commands" in vars(cls):
			if direct or cls.declared:
				raise ValueError(
					f"{cls.__name__} cannot declare both commands and values or run()"
				)
			check_commands(cls)
		elif not direct:
			raise ValueError(f"{cls.__name__} must declare commands or override run()")

	@classmethod
	def main(cls, argv: list[str]) -> object:
		from luna.cli.parse import parse

		# If the provided argv includes the current program, drop it.
		if argv and argv[0] == sys.argv[0]:
			argv = argv[1:]

		try:
			result = parse(cls, argv)
		except HelpRequested as requested:
			print(requested.help, end="")
			return None
		except ParseError as error:
			print(error.usage, end="", file=sys.stderr)
			print(f"{cls.name}: error: {error.message}", file=sys.stderr)
			raise SystemExit(2) from None

		if result.command is not None:
			return result.command(**result.values).run()
		return result.program(**result.values).run()


def check_name(owner: type):
	name = vars(owner).get("name")
	if not isinstance(name, str) or not name:
		raise ValueError(f"{owner.__name__} must set name to a nonempty string")
	if name.startswith("-"):
		raise ValueError(f"{owner.__name__}.name must not begin with '-': {name!r}")


def check_commands(program: type[Program]):
	commands = program.commands
	if not commands:
		raise ValueError(f"{program.__name__}.commands must list at least one command")

	names = set()
	for command in commands:
		if not isinstance(command, type) or not issubclass(command, Command):
			# Invalid declarations raise ValueError at class creation.
			raise ValueError(  # noqa: TRY004
				f"{program.__name__}.commands contains a non-Command entry: {command!r}"
			)
		if command.name in names:
			raise ValueError(
				f"{program.__name__}.commands has duplicate name: {command.name!r}"
			)
		names.add(command.name)
