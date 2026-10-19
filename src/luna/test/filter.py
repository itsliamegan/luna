from abc import ABC, abstractmethod

from luna.test.group import Group
from luna.test.test import Test


class Filter(ABC):
	@abstractmethod
	def match(self, group: Group, test: Test) -> bool: ...


class NameFilter(Filter):
	def __init__(self, name: str):
		self.name = name

	def match(self, group: Group, test: Test) -> bool:
		return self.name in group.name
