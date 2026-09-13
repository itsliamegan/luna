# Argv parsing

## Goal

Add a small declarative command-line parsing API to `luna.argv`, using standard
`argparse` grammar and behavior wherever possible. It supports either a single
program with arguments and options or a program containing subcommands. Parsing
is separate from handler execution, does not print, and never exits the process.

Handler invocation and the complete `Program.run()` contract are intentionally
left for a follow-up design pass. The parse result will nevertheless be shaped
so a later runner can invoke a handler with `handler(**result.values)`.

## Public API

Add `src/luna/argv.py` with these public types:

- `Argument`
- `Option`
- `Command`
- `Program`
- `ParseResult`
- `ParseError`
- `HelpRequested`

The initial declaration shape should be equivalent to:

```python
program = Program(
	name="copy",
	description="Copy a file.",
	arguments=[
		Argument("source", type=str),
		Argument("destination", type=str, required=False),
	],
	options=[
		Option("count", short="c", type=int, default=1),
		Option("verbose", short="v", type=bool),
		Option("tag", short="t", type=list[str]),
	],
)

result = program.parse(["input.txt", "--count=2", "--verbose"])
```

`ParseResult` contains:

```python
@dataclass(frozen=True)
class ParseResult:
	program: Program
	command: Command | None
	values: dict[str, object]
```

Declarations use ordinary lists for their argument, option, and command
collections. Constructors accept `None` for an omitted collection and create a
fresh list rather than sharing a mutable default. `ParseResult.values` is an
ordinary dict.

Names are required and declaration types default to `str`. Constructor
parameters may be passed positionally or by keyword; do not make them
positional-only or keyword-only. `Argument` and `Option` accept optional
`help` text. Positional requiredness is explicit: `Argument` defaults to
`required=True`, while `required=False` makes it optional. `Option` defaults to
`required=False`. Defaults use `None` directly; no missing-value sentinel is
needed.

Use ordinary mutable dataclasses for declarations. Their collection fields are
ordinary lists created with fresh defaults. Keep the model simple rather than
adding immutability or read-only wrappers.

`values` uses declaration names unchanged. There is no destination-name or
hyphen-to-underscore normalization: `Option("output_path")` is spelled
`--output_path` and produces the keyword `output_path`.

Every declaration contributes a value so eventual handler signatures remain
stable:

- required positional: its parsed value;
- omitted optional positional: its non-`None` default, or `None`;
- omitted scalar option: its non-`None` default, or `None`;
- omitted boolean option: its non-`None` default, or `False`;
- omitted list option: a fresh copy of its non-`None` default, or a fresh empty
  list.

Never expose a mutable list owned by a declaration or reuse a generated empty
list between parses.

## Declaration rules

Validate definitions when constructing a `Program` or `Command`, before parsing
argv:

- A `Program` is either a direct program or a command collection.
- A direct program may contain arguments and options but no commands.
- A command collection may contain commands but no program-level arguments,
  options, or direct invocation values.
- Argument and option names must be valid, non-keyword Python identifiers.
- Argument and option names share one result namespace and must be unique.
- `h` and `help` are reserved option names/aliases.
- A short alias is optional, consists of exactly one ASCII letter, and must not
  collide with another option's canonical name or alias. An option whose
  one-letter canonical name matches its own short alias is allowed.
- Command names must be unique, nonempty tokens that do not begin with `-`.
- Positional arguments support only `str` and `int` initially.
- Required positional arguments must precede optional positional arguments.
- Positional arguments are required by default and become optional only through
  `required=False`; supplying a default does not change requiredness.
- A required positional argument cannot have a non-`None` default.
- Positional `bool` and `list[T]` declarations are rejected.
- Options support `str`, `int`, `bool`, `list[str]`, and `list[int]`.
- Bare `list` and unsupported or nested list element types are rejected.
- Boolean options are presence flags and default to `False` when no default is
  declared.
- List options default to a fresh empty list for each parse when no default is
  declared; declared list defaults are copied for each parse.
- A required option cannot have a non-`None` default.
- Non-`None` defaults are validated exactly against their declared types;
  notably, `bool` is not accepted as an `int`. `None` represents the absence of
  a configured default and is normalized according to the declaration kind
  during parsing.

Raise `ValueError` for invalid declarations. Reserve `ParseError` for invalid
user input.

## Accepted grammar

Use argparse's conventional option spelling and parsing behavior rather than a
Luna-specific strict grammar.

### Direct programs and selected commands

- Canonical options use two dashes: `--name`.
- One-letter aliases use one dash: `-n`.
- Scalar and list values accept argparse's separated and attached forms, such as
  `--name=value`, `--name value`, `-nvalue`, and `-n=value`.
- Options can be interspersed with positional arguments to the extent supported
  by normal `ArgumentParser.parse_args()` behavior.
- `--` ends option parsing; every following token is positional, including
  tokens beginning with `-`.
- Long-option abbreviation and short-option grouping use argparse's defaults.
  For example, an unambiguous `--ver` may select `--verbose`, and boolean short
  aliases may be grouped as `-abc`.
- Unknown or ambiguous options and unexpected positional values are errors.
- Repeating a scalar option uses argparse's normal last-value-wins behavior.
- Repeating a boolean presence flag is accepted and leaves it true.
- A boolean accepts no explicit value; for example, `--verbose=true` is an
  error.
- A list option may be repeated and preserves encounter order. If the option is
  supplied, parsed values replace rather than extend its declared default; the
  declared default is used only when the option is omitted.
- Integers use Python's `int` conversion and strings are retained verbatim.
  Negative-number handling follows argparse.

### Command collections

- Before command selection, the only declared switches are `--help` and `-h`.
- Bare invocation is a missing-command parse error and carries top-level usage.
- Other pre-command input follows argparse's normal unknown-option or invalid
  command behavior.
- Once selected, the command parses the remaining argv using the direct-program
  grammar.
- `--` cannot be used to bypass command selection.

## Errors and help

`Program.parse(argv)` accepts argv without the executable name. It never reads
`sys.argv`, writes to a stream, or raises `SystemExit`.

- Malformed input raises `ParseError`.
- A help request raises the separate `HelpRequested` control-flow exception.
- `ParseError` has public `message: str` and `usage: str` attributes.
  `str(error)` returns only the concise message.
- `HelpRequested` has a public `help: str` attribute. `str(request)` returns the
  complete rendered help text.
- The exceptions retain argparse's rendered usage/help text so a later
  `Program.run()` can choose the stream and exit status.
- Program help uses `--help` and `-h` and lists available commands for a command
  collection.
- Command help is available as `<command> --help` and `<command> -h`.
- Help exits parsing before handler execution and is not represented as a
  `ParseResult`.

Neither exception prints or exits. Exit statuses remain the future runner's
responsibility, and callers never need to parse a formatted exception string to
inspect a parse failure.

## Implementation approach

Use `argparse` as a private implementation detail and deliberately preserve its
normal parsing behavior. Do not expose its parser, namespace, actions, or
exceptions publicly.

1. Compile each direct `Program` or `Command` declaration into a private
   `ArgumentParser`. Keep argparse's parsing defaults, including abbreviation
   and short-option handling.
2. Register canonical options as `--name` and aliases as `-n`. Use argparse's
   standard `type`, `required`, `default`, `nargs`, `store_true`, and `append`
   facilities rather than prevalidating tokens or implementing custom parsing
   actions.
3. Use `typing.get_origin()` and `typing.get_args()` to recognize supported
   `list[T]` declarations. Configure list options with `action="append"` and a
   one-value occurrence so repetitions produce one flat, ordered list.
4. Configure required positionals normally and trailing optional positionals
   with `nargs="?"` and their defaults.
5. Disable argparse's built-in help action only because it prints and exits.
   Add `--help` and `-h` through a small custom action that raises
   `HelpRequested` with `parser.format_help()` instead.
6. Override the parser's error path so malformed input raises `ParseError` with
   a concise message and `parser.format_usage()`, without printing or exiting.
7. Use argparse subparsers if they preserve the required exception and result
   contracts cleanly; otherwise select the command before delegating to its
   compiled parser. Do not recreate parsing behavior merely to customize error
   wording.
8. Convert the private namespace into a fresh `values` mapping, copying mutable
   defaults, and return only Luna's `ParseResult`.

## Tests

Add `test/test/argv_test.py`, covering at least:

### Definitions

- valid direct and command-based declarations;
- rejection of mixed program arguments/options and commands;
- duplicate names and aliases, including reserved help names;
- invalid Python identifiers and command names;
- required-after-optional positional ordering;
- accepted and rejected positional/option types;
- bare and nested lists;
- explicit positional requiredness and defaults;
- valid and invalid non-`None` defaults;
- required arguments and options with non-`None` defaults.

### Direct parsing

- required and optional positionals, including omitted defaults;
- multiple optional positionals populated left-to-right;
- canonical long and short option spellings;
- argparse's separated and attached scalar value forms;
- interspersed options and positionals;
- boolean presence and omission;
- rejection of explicit boolean values;
- repeated typed lists with stable ordering and fresh empty defaults;
- argparse's repeated-scalar, repeated-boolean, long-abbreviation, and grouped
  short-alias behavior;
- unknown and ambiguous options;
- integer conversion failures and negative integers;
- missing and excess positionals;
- `--` with dash-prefixed positional values.

### Commands and help

- known command selection and `ParseResult.command`;
- bare invocation and unknown commands;
- rejection of non-help program-level switches;
- top-level and command-level help;
- argparse-formatted help containing descriptions, argument and option help
  text, arguments, options, aliases, and commands as appropriate;
- confirmation that parse errors/help do not print or exit.

## Documentation

Update `README.md` to list the argv library and show one direct-program example
and one command-collection example. Document conventional `--long` and `-s`
option spelling, underscore naming, argparse-compatible abbreviation/grouping,
repeated list options, `--`, parse exceptions, and the fact that execution is
separate and will be added later.

## Verification

From the Luna repository, run:

```text
mise run test
mise run lint
mise run check
```

Do not consider implementation complete until all three pass.

## Remaining work

- Update `README.md` with direct-program and command-collection examples and the
  parsing conventions described above.
- Perform a final implementation and test review, then run the complete
  verification commands once more.
