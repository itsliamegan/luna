# Luna

Luna is a collection of Python support libraries. They include:

- A [testing library](src/luna/test/__init__.py), including
  [assertions](src/luna/test/assertion.py) and a default
  [runner](src/luna/test/runner.py).
- A [declarative CLI library](src/luna/cli/__init__.py) that wraps `argparse`.
- [Inflection helpers](src/luna/inflect.py) that convert between word
  representations.

## CLI

A program declares each value once, as an annotated class attribute. Its
`run()` method reads the parsed values from `self`:

```python
import sys

from luna.cli import Program, option


class Backup(Program):
	"""Back up the database."""

	name = "backup"
	dry: bool = option(short="d", help="report what would be uploaded")
	keep: int = option(7, short="k", help="days of backups to retain")

	def run(self): ...


if __name__ == "__main__":
	Backup.main(sys.argv)
```

A program can instead collect commands, selected by the first argument:

```python
from luna.cli import Command, Program, argument


class Apply(Command):
	"""Apply pending migrations."""

	name = "apply"
	target: str = argument("latest", help="migration to apply up to")

	def run(self): ...


class Status(Command):
	"""Report pending migrations."""

	name = "status"

	def run(self): ...


class Migrate(Program):
	name = "migrate"
	commands = [Apply, Status]
```

`argument()` declares a positional argument. `option()`, a plain default, or no
default at all declare an `--option`; a value without a default is required.
Instances can also be constructed directly, as in `Apply(target="v2").run()`.
