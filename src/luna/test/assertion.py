from types import TracebackType
from typing import Self


class RaisedException[ExceptionT: BaseException]:
	def __init__(self, exception_type: type[ExceptionT]):
		self.exception_type = exception_type
		self.exception: ExceptionT | None = None

	def __enter__(self) -> Self:
		return self

	def __exit__(
		self,
		exception_type: type[BaseException] | None,
		exception: BaseException | None,
		traceback: TracebackType | None,
	) -> bool:
		if exception is None:
			raise AssertionError(f"expected: raise {self.exception_type.__name__}")
		if not isinstance(exception, self.exception_type):
			return False

		self.exception = exception
		return True


def assert_that(value: object, message: str | None = None) -> None:
	if not value:
		raise AssertionError(
			message if message is not None else f"expected: truthy\nactual:   {value!r}"
		)


def assert_not(value: object, message: str | None = None) -> None:
	if value:
		raise AssertionError(
			message if message is not None else f"expected: falsy\nactual:   {value!r}"
		)


def assert_eq(actual: object, expected: object, message: str | None = None) -> None:
	if actual != expected:
		raise AssertionError(
			message
			if message is not None
			else f"expected: {expected!r}\nactual:   {actual!r}"
		)


def assert_not_eq(actual: object, expected: object, message: str | None = None) -> None:
	if actual == expected:
		raise AssertionError(
			message
			if message is not None
			else f"expected: different\nactual:   {actual!r}"
		)


def assert_raises[ExceptionT: BaseException](
	exception_type: type[ExceptionT],
) -> RaisedException[ExceptionT]:
	return RaisedException(exception_type)
