import sys


class Logger:
	def info(self, message: str):
		print(message, file=sys.stderr)

	def warn(self, message: str):
		print(f"warning: {message}", file=sys.stderr)

	def error(self, message: str):
		print(f"error: {message}", file=sys.stderr)
