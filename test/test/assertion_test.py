from luna.test.assertion import (
	assert_eq,
	assert_not,
	assert_not_eq,
	assert_raises,
	assert_that,
)


def test_truthiness_assertions():
	assert_that(1)
	assert_not(0)

	assert str(raised_by(lambda: assert_that(0))) == "expected: truthy\nactual:   0"
	assert str(raised_by(lambda: assert_not(1))) == "expected: falsy\nactual:   1"


def test_equality_assertions():
	assert_eq({"name": "Alice"}, {"name": "Alice"})
	assert_not_eq("Alice", "Bob")

	assert (
		str(raised_by(lambda: assert_eq("Alice", "Bob")))
		== "expected: 'Bob'\nactual:   'Alice'"
	)
	assert str(raised_by(lambda: assert_not_eq("Bob", "Bob"))) == (
		"expected: different\nactual:   'Bob'"
	)


def test_custom_messages():
	assert str(raised_by(lambda: assert_that(False, "not true"))) == "not true"
	assert str(raised_by(lambda: assert_eq(1, 2, "not equal"))) == "not equal"


def test_assert_raises():
	with assert_raises(ValueError):
		int("not an integer")


def test_assert_raises_exposes_exception():
	with assert_raises(ValueError) as raised:
		int("not an integer")

	assert isinstance(raised.exception, ValueError)
	assert "not an integer" in str(raised.exception)


def test_assert_raises_fails_when_nothing_is_raised():
	def raise_nothing():
		with assert_raises(ValueError):
			pass

	assert str(raised_by(raise_nothing)) == "expected: raise ValueError"


def test_assert_raises_does_not_hide_unexpected_exceptions():
	try:
		with assert_raises(TypeError):
			raise ValueError("unexpected")
	except ValueError as err:
		assert str(err) == "unexpected"
	else:
		raise AssertionError("Expected the unexpected exception to propagate")


def raised_by(fn):
	try:
		fn()
	except AssertionError as err:
		return err
	raise AssertionError("Expected an AssertionError")
