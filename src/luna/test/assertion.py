from collections.abc import Container
from difflib import ndiff
from pprint import pformat
from types import TracebackType
from typing import Self


class RaisedException[ExceptionT: BaseException]:
	def __init__(self, exception_type: type[ExceptionT]):
		self.exception_type = exception_type
		self._exception: ExceptionT | None = None

	@property
	def exception(self) -> ExceptionT:
		if self._exception is None:
			raise AssertionError("no exception captured")
		return self._exception

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

		self._exception = exception
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
			message if message is not None else difference(expected, actual)
		)


def assert_not_eq(actual: object, expected: object, message: str | None = None) -> None:
	if actual == expected:
		raise AssertionError(
			message
			if message is not None
			else f"expected: different\nactual:   {actual!r}"
		)


def assert_in(
	item: object,
	container: Container[object],
	message: str | None = None,
):
	if item not in container:
		raise AssertionError(
			message
			if message is not None
			else f"expected: contains {item!r}\nactual:   {container!r}"
		)


def assert_not_in(
	item: object,
	container: Container[object],
	message: str | None = None,
):
	if item in container:
		raise AssertionError(
			message
			if message is not None
			else f"expected: excludes {item!r}\nactual:   {container!r}"
		)


def assert_is(actual: object, expected: object, message: str | None = None):
	if actual is not expected:
		raise AssertionError(
			message
			if message is not None
			else f"expected: same object as {expected!r}\nactual:   {actual!r}"
		)


def assert_is_not(actual: object, expected: object, message: str | None = None):
	if actual is expected:
		raise AssertionError(
			message
			if message is not None
			else f"expected: different object\nactual:   {actual!r}"
		)


def assert_not_none[T](value: T | None, message: str | None = None) -> T:
	if value is None:
		raise AssertionError(
			message if message is not None else "expected: not None\nactual:   None"
		)
	return value


def assert_is_instance[T](
	value: object,
	type_: type[T],
	message: str | None = None,
) -> T:
	if not isinstance(value, type_):
		raise AssertionError(  # noqa: TRY004
			message
			if message is not None
			else f"expected: instance of {type_.__name__}\nactual:   {value!r}"
		)
	return value


def assert_raises[ExceptionT: BaseException](
	exception_type: type[ExceptionT],
) -> RaisedException[ExceptionT]:
	return RaisedException(exception_type)


def difference(expected: object, actual: object) -> str:
	# Strings are compared as text, because their repr would put every line on
	# one line with escaped newlines.
	if isinstance(expected, str) and isinstance(actual, str):
		expected_text = expected
		actual_text = actual
	else:
		expected_text = pformat(expected, sort_dicts=False)
		actual_text = pformat(actual, sort_dicts=False)

	if "\n" not in expected_text and "\n" not in actual_text:
		return f"expected: {expected!r}\nactual:   {actual!r}"

	# ndiff ends its hint lines with a newline whatever the input, so input lines
	# keep their own and every output line is stripped before joining. Keeping
	# them also shows a missing trailing newline as a changed line.
	lines = ndiff(
		expected_text.splitlines(keepends=True),
		actual_text.splitlines(keepends=True),
	)
	diff = "\n".join(line.rstrip("\n") for line in lines)
	return f"expected: -, actual: +\n{diff}"
