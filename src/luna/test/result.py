from dataclasses import dataclass

from luna.test.location import Location
from luna.test.output import Output

type Result = Pass | Fail | Error


@dataclass
class Pass:
	group_name: str
	test_name: str
	output: Output


@dataclass
class Fail:
	group_name: str
	test_name: str
	error: str
	output: Output
	location: Location | None = None


@dataclass
class Error:
	group_name: str
	test_name: str
	error: str
	output: Output
