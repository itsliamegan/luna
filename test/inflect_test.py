from luna.inflect import count, dash, sentence, words
from luna.test.assertion import assert_eq


def test_splits_names_into_words():
	assert_eq(words("board_ids"), ["board", "ids"])
	assert_eq(words("class_"), ["class"])
	assert_eq(words("_private"), ["private"])
	assert_eq(words("a__b"), ["a", "b"])
	assert_eq(words("title"), ["title"])


def test_writes_names_as_sentences():
	assert_eq(sentence("open_in_new_tab"), "Open in new tab")
	assert_eq(sentence("class_"), "Class")
	assert_eq(sentence("_private"), "Private")
	assert_eq(sentence("a__b"), "A b")
	assert_eq(sentence("title"), "Title")


def test_leaves_the_rest_of_a_sentence_as_written():
	assert_eq(sentence("return_to_URL"), "Return to URL")


def test_joins_names_with_dashes():
	assert_eq(dash("data_turbo_frame"), "data-turbo-frame")
	assert_eq(dash("class_"), "class")
	assert_eq(dash("_private"), "private")
	assert_eq(dash("a__b"), "a-b")
	assert_eq(dash("title"), "title")


def test_counts_with_a_singular_or_plural_unit():
	assert_eq(count(1, "item"), "1 item")
	assert_eq(count(0, "item"), "0 items")
	assert_eq(count(3, "item"), "3 items")


def test_counts_with_an_irregular_plural():
	assert_eq(count(1, "entry", "entries"), "1 entry")
	assert_eq(count(2, "entry", "entries"), "2 entries")
