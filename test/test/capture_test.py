from luna.test import capture
from luna.test.assertion import assert_that
from luna.test.output import Output
from luna.test.result import Error, Fail, Pass


def test_always_capture_shows_no_output():
	always = capture.Always()

	assert_that(not always.shows(Pass("user_test", "test_create", Output("", ""))))
	assert_that(not always.shows(Fail("user_test", "test_create", "", Output("", ""))))
	assert_that(
		not always.shows(Error("user_test", "test_create", "", Output("", ""))),
	)


def test_pass_capture_shows_failing_output():
	passing = capture.Pass()

	assert_that(not passing.shows(Pass("user_test", "test_create", Output("", ""))))
	assert_that(passing.shows(Fail("user_test", "test_create", "", Output("", ""))))
	assert_that(passing.shows(Error("user_test", "test_create", "", Output("", ""))))


def test_never_capture_shows_all_output():
	never = capture.Never()

	assert_that(never.shows(Pass("user_test", "test_create", Output("", ""))))
	assert_that(never.shows(Fail("user_test", "test_create", "", Output("", ""))))
	assert_that(never.shows(Error("user_test", "test_create", "", Output("", ""))))
