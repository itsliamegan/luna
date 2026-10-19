from dataclasses import dataclass
import linecache
from pathlib import Path
import textwrap
import traceback
from types import TracebackType


@dataclass
class Location:
	path: Path
	line: int
	source: str

	@staticmethod
	def from_traceback(
		traceback_start: TracebackType | None,
		path: Path,
	) -> Location | None:
		# Frames run from outermost to innermost, so the first frame in the test
		# file is the line in the test function. Later frames in the same file
		# belong to helpers it called and are skipped.
		for frame in traceback.extract_tb(traceback_start):
			if Path(frame.filename) != path or frame.lineno is None:
				continue

			end = frame.end_lineno or frame.lineno
			lines = linecache.getlines(frame.filename)[frame.lineno - 1 : end]
			source = textwrap.dedent("".join(lines)).rstrip()
			return Location(path, frame.lineno, source)
		return None
