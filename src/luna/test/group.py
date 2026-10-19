from dataclasses import dataclass
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import ModuleType

from luna.test.test import Test


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
