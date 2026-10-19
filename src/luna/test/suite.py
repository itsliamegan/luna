from dataclasses import dataclass
from pathlib import Path

from luna.test.filter import Filter
from luna.test.group import Group
from luna.test.test import Test


@dataclass
class Suite:
	groups: list[Group]

	@classmethod
	def discover(cls, path: Path) -> Suite:
		groups = []
		for directory, directories, files in path.walk():
			directories.sort()
			for file_name in sorted(files):
				file = Path(directory, file_name)
				if file.suffix != ".py" or not file.stem.endswith("_test"):
					continue

				name = file.relative_to(path).with_suffix("").as_posix()
				group = Group(name, file.resolve(), [])
				module = group.import_module()
				for attribute, item in module.__dict__.items():
					if attribute.startswith("test") and callable(item):
						group.tests.append(Test(attribute))
				groups.append(group)
		return Suite(groups)

	def select(self, filter: Filter) -> Suite:
		groups = []
		for group in self.groups:
			tests = []
			for test in group.tests:
				if filter.match(group, test):
					tests.append(test)
			if tests:
				groups.append(Group(group.name, group.path, tests))
		return Suite(groups)
