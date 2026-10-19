from dataclasses import dataclass
from enum import StrEnum
from typing import ClassVar

from luna.ansi import Escape
from luna.test.location import Location
from luna.test.test import Test


class Status(StrEnum):
	PASS = "pass"
	FAIL = "fail"
	ERROR = "error"

	@property
	def failing(self) -> bool:
		match self:
			case Status.PASS:
				return False
			case Status.FAIL | Status.ERROR:
				return True

	@property
	def label(self) -> str:
		match self:
			case Status.PASS:
				return "PASS"
			case Status.FAIL:
				return "FAIL"
			case Status.ERROR:
				return "ERROR"

	@property
	def color(self) -> Escape:
		match self:
			case Status.PASS:
				return Escape.GREEN
			case Status.FAIL:
				return Escape.RED
			case Status.ERROR:
				return Escape.YELLOW


type Result = Pass | Fail | Error


@dataclass
class Pass:
	status: ClassVar[Status] = Status.PASS

	test: Test
	output: str


@dataclass
class Fail:
	status: ClassVar[Status] = Status.FAIL

	test: Test
	output: str
	message: str
	location: Location | None


@dataclass
class Error:
	status: ClassVar[Status] = Status.ERROR

	test: Test
	output: str
	traceback: str
