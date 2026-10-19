from dataclasses import dataclass

from luna.test.location import Location
from luna.test.test import Test

type Result = Pass | Fail | Error


@dataclass
class Pass:
	test: Test
	output: str


@dataclass
class Fail:
	test: Test
	output: str
	message: str
	location: Location | None


@dataclass
class Error:
	test: Test
	output: str
	traceback: str
