from luna.test import capture
from luna.test.assertion import assert_that
from luna.test.result import Error, Fail, Pass
from luna.test.test import Test


def test_always_capture_shows_no_output():
	always = capture.Always()

	assert_that(not always.shows(Pass(Test("test_create"), "")))
	assert_that(not always.shows(Fail(Test("test_create"), "", "", None)))
	assert_that(
		not always.shows(Error(Test("test_create"), "", "")),
	)


def test_only_pass_capture_shows_failing_output():
	only_pass = capture.OnlyPass()

	assert_that(not only_pass.shows(Pass(Test("test_create"), "")))
	assert_that(only_pass.shows(Fail(Test("test_create"), "", "", None)))
	assert_that(only_pass.shows(Error(Test("test_create"), "", "")))


def test_never_capture_shows_all_output():
	never = capture.Never()

	assert_that(never.shows(Pass(Test("test_create"), "")))
	assert_that(never.shows(Fail(Test("test_create"), "", "", None)))
	assert_that(never.shows(Error(Test("test_create"), "", "")))
