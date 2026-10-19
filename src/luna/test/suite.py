from abc import ABC, abstractmethod
from dataclasses import dataclass
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import ModuleType


@dataclass
class Suite:
	groups: list[Group]

	@classmethod
	def discover(cls, path: Path) -> Suite:
		groups = []
		for dir, dirs, files in path.walk():
			dirs.sort()
			for file_name in sorted(files):
				file = Path(dir, file_name)
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


@dataclass
class Group:
	name: str
	path: Path
	tests: list[Test]

	def import_module(self) -> ModuleType:
		spec = spec_from_file_location(self.name.replace("/", "."), self.path)
		if spec is None or spec.loader is None:
			raise ImportError(f"Cannot load test module from {self.path}")

		module = module_from_spec(spec)
		spec.loader.exec_module(module)
		return module


@dataclass
class Test:
	name: str


class Filter(ABC):
	@abstractmethod
	def match(self, group: Group, test: Test) -> bool: ...
