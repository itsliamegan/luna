# Test Output Capture Plan

## Goal

Keep test output quiet by default while supporting both debugging and assertions against stdout/stderr.

## Proposed interface

Separate whether output is captured from whether captured output is displayed:

- Capture stdout and stderr for every test case by default.
- Store captured streams on each `Result`.
- Add `--show-output=never|failures|always`:
  - `never` remains the default.
  - `failures` prints output only for failed/erroring cases.
  - `always` prints output for every case.
- Add `--no-capture` to run tests against the process's real streams. This is intended for interactive debugging and tools that inspect or depend on real streams.
- Add an explicit `capture_output()` context manager for tests that need to assert output without depending on runner internals:

```python
with capture_output() as output:
	program()

assert output.stdout == "hello\n"
assert output.stderr == ""
```

## Implementation steps

1. Introduce an output value type containing `stdout` and `stderr` strings.
2. Extend `Result` (and therefore `Pass`, `Fail`, and `Error`) with captured output.
3. Change `Case.run()` to accept a capture policy rather than unconditionally replacing `sys.stdout` and `sys.stderr`.
4. Ensure stream restoration is exception-safe and preserve the traceback behavior currently used by error reporting.
5. Add CLI parsing for the output-display option and `--no-capture`, while retaining the existing optional test-name filter.
6. Pass capture configuration through `Suite.run()` and `Test.run()` to `Case.run()`.
7. Update `report()` to render captured stdout and stderr according to the selected display policy, clearly labeling and indenting each stream.
8. Implement and export `capture_output()` as a standalone context manager. It should restore streams safely and support nested use.
9. Document the CLI options and the output-testing API in the README.

## Tests

- Output remains hidden with default settings.
- stdout and stderr are captured independently on passing, failing, and erroring cases.
- `failures` displays output only for `Fail` and `Error` results.
- `always` displays output for all results.
- Empty streams do not produce headings or blank output sections.
- `--no-capture` leaves the active streams in place and does not replay output in the report.
- Streams are restored after passes, assertion failures, and unexpected exceptions.
- `capture_output()` captures both streams, exposes strings, restores streams, and behaves correctly when nested.
- Existing test-name filtering continues to work when combined with output options.
- Invalid CLI values produce a useful usage error.

## Open decisions

- Whether the option should be named `--show-output` or use a shorter conventional alias such as `-s` for `--no-capture`.
- Whether `failures` should eventually become the default once output capture is stored on results.
- Whether captured output should be retained when `--no-capture` is active (doing so would require tee streams rather than true no-capture behavior).
