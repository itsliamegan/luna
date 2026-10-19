from pathlib import Path
from tempfile import TemporaryDirectory

from luna.test.assertion import assert_eq
from luna.test.filter import Filter
from luna.test.group import Group
from luna.test.suite import Suite
from luna.test.test import Test


def test_discovers_nested_tests():
	with TemporaryDirectory() as temporary_directory:
		test_directory = Path(temporary_directory, "test")
		path = Path(test_directory, "unit", "models", "user_test.py")
		path.parent.mkdir(parents=True)
		path.write_text("def test_create():\n\tpass\n")

		suite = Suite.discover(test_directory)

	assert_eq(len(suite.groups), 1)
	assert_eq(suite.groups[0].name, "unit/models/user_test")
	assert_eq(suite.groups[0].tests[0].name, "test_create")


def test_discovers_files_before_subdirectories():
	with TemporaryDirectory() as temporary_directory:
		test_directory = Path(temporary_directory, "test")
		Path(test_directory, "models").mkdir(parents=True)
		Path(test_directory, "orders").mkdir()
		for name in [
			"user_test.py",
			"models/user_test.py",
			"orders/order_test.py",
			"account_test.py",
		]:
			Path(test_directory, name).write_text("def test_create():\n\tpass\n")

		suite = Suite.discover(test_directory)

	names = []
	for group in suite.groups:
		names.append(group.name)
	assert_eq(
		names,
		["account_test", "user_test", "models/user_test", "orders/order_test"],
	)


def test_discovers_tests_in_declaration_order():
	with TemporaryDirectory() as temporary_directory:
		test_directory = Path(temporary_directory, "test")
		test_directory.mkdir()
		Path(test_directory, "user_test.py").write_text(
			"def test_update():\n\tpass\n\n"
			"def test_create():\n\tpass\n\n"
			"def test_delete():\n\tpass\n"
		)

		suite = Suite.discover(test_directory)

	names = []
	for test in suite.groups[0].tests:
		names.append(test.name)
	assert_eq(names, ["test_update", "test_create", "test_delete"])


def test_selects_matching_tests():
	suite = Suite(
		[
			Group(
				"user_test",
				Path("test", "user_test.py"),
				[Test("test_create"), Test("test_delete")],
			),
		]
	)

	selected = suite.select(NamedTestFilter("test_delete"))

	assert_eq(selected.groups[0].tests, [Test("test_delete")])


def test_drops_groups_without_selected_tests():
	suite = Suite(
		[
			Group("order_test", Path("test", "order_test.py"), [Test("test_place")]),
			Group("user_test", Path("test", "user_test.py"), [Test("test_create")]),
		]
	)

	selected = suite.select(NamedTestFilter("test_create"))

	assert_eq(len(selected.groups), 1)
	assert_eq(selected.groups[0].name, "user_test")


class NamedTestFilter(Filter):
	def __init__(self, name: str):
		self.name = name

	def match(self, group: Group, test: Test) -> bool:
		return test.name == self.name
