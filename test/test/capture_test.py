from luna.test.assertion import assert_that
from luna.test.capture import AlwaysCapture, NeverCapture, PassCapture
from luna.test.output import Output
from luna.test.result import Error, Fail, Pass


def test_always_capture_shows_no_output():
	capture = AlwaysCapture()

	assert_that(not capture.shows(Pass("user_test", "test_create", Output("", ""))))
	assert_that(not capture.shows(Fail("user_test", "test_create", "", Output("", ""))))
	assert_that(
		not capture.shows(Error("user_test", "test_create", "", Output("", ""))),
	)


def test_pass_capture_shows_failing_output():
	capture = PassCapture()

	assert_that(not capture.shows(Pass("user_test", "test_create", Output("", ""))))
	assert_that(capture.shows(Fail("user_test", "test_create", "", Output("", ""))))
	assert_that(capture.shows(Error("user_test", "test_create", "", Output("", ""))))


def test_never_capture_shows_all_output():
	capture = NeverCapture()

	assert_that(capture.shows(Pass("user_test", "test_create", Output("", ""))))
	assert_that(capture.shows(Fail("user_test", "test_create", "", Output("", ""))))
	assert_that(capture.shows(Error("user_test", "test_create", "", Output("", ""))))
