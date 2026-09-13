# Simple Assertion Rewriting for Testing Frameworks

A practical guide to implementing assertion introspection without the full complexity of pytest's approach.

## Overview

When building a testing framework, you often want assertions to display intermediate values on failure:

```python
# Without rewriting:
AssertionError: assert False

# With rewriting:
AssertionError: assert x == y
  where:
    x = 4
    y = 5
Markdown

# Simple Assertion Rewriting for Testing Frameworks

A practical guide to implementing assertion introspection without the full complexity of pytest's approach.

## Overview

When building a testing framework, you often want assertions to display intermediate values on failure:

```python
# Without rewriting:
AssertionError: assert False

# With rewriting:
AssertionError: assert x == y
  where:
    x = 4
    y = 5
```

This guide shows how to implement this in ~300 lines of code by handling the common cases well and gracefully falling back for edge cases.

## Why This Approach?

Pytest's assertion rewriting is ~1200 lines because it:

    Handles all Python operators perfectly
    Respects short-circuit evaluation in and/or
    Manages the format context stack for nested expressions
    Supports walrus operators (:=)
    Caches rewritten bytecode
    Runs an import hook system

For most testing frameworks, you don't need all that. This guide focuses on:

    ✅ Comparisons (==, !=, <, >, etc.)
    ✅ Simple boolean operators (and, or)
    ✅ Function calls and attributes
    ❌ Short-circuit optimization
    ❌ Walrus operators
    ❌ Import hook complexity

Real-world impact: ~95% of test assertions are comparisons. You get 80% of the value with 25% of the code.

## Architecture

The key concept: rewrite asserts into assignment statements followed by conditionals.
Before:

```python

assert x == y

After:

```python

@py_assert0 = x
@py_assert1 = y
if not (@py_assert0 == @py_assert1):
    msg = _build_assertion_message("x == y", {"@py_assert0": repr(x), "@py_assert1": repr(y)})
    raise AssertionError(msg)
```

This gives you:

    Captured intermediate values in variables
    Access to those values when building the error message
    The original comparison still works normally

## Implementation

### 1. The AST Rewriter

The core is an ast.NodeVisitor that handles different expression types:

```python
import ast
from typing import Any


class SimpleAssertRewriter(ast.NodeVisitor):
	"""Rewrite assert statements for better error messages."""

	def __init__(self):
		self.var_counter = 0
		self.statements = []  # Accumulated statements to insert
		self.captured = {}  # Variable name -> original AST expression
```

Related pytest code: See AssertionRewriter class in src/_pytest/assertion/rewrite.py:598

### 2. Handle Comparisons (Most Important)

Comparisons like a == b, x > y, or chained a < b < c are by far the most common assertion pattern:
```python
def visit_Compare(self, node: ast.Compare) -> tuple[ast.expr, dict]:
	"""Handle: a == b, x > y, a < b < c, etc."""

	# Capture the left operand
	left_var = self.fresh_var()  # e.g., "@py_assert0"
	self.statements.append(ast.Assign([ast.Name(left_var, ast.Store())], node.left))

	captures = {left_var: node.left}

	# Capture each comparator (right side of each operator)
	for op, comparator in zip(node.ops, node.comparators):
		comp_var = self.fresh_var()
		self.statements.append(
			ast.Assign([ast.Name(comp_var, ast.Store())], comparator)
		)
		captures[comp_var] = comparator

	# Return modified comparison using captured variable names
	new_left = ast.Name(left_var, ast.Load())
	new_comparators = [
		ast.Name(f"@py_assert{i + 1}", ast.Load()) for i in range(len(node.comparators))
	]

	new_comparison = ast.Compare(new_left, node.ops, new_comparators)
	return new_comparison, captures
```

Why comparisons are special:

    Python allows chained comparisons: a < b < c (evaluated as a < b and b < c)
    We want to capture a, b, and c to show all values
    This is fundamentally different from binary operators

Related pytest code: See visit_Compare() in src/_pytest/assertion/rewrite.py:1103-1146

Note: Pytest's version is much more complex because it handles:

    Format context stacks (lines 1104, 1146)
    Walrus operators (lines 1108-1109, 1123-1124)
    Custom comparison representations via _call_reprcompare() (lines 1134-1140)

### 3. Handle Boolean Operators (Simplified)

For and/or, the simple approach is to evaluate both sides eagerly (no short-circuit optimization):

```python
def visit_BoolOp(self, node: ast.BoolOp) -> tuple[ast.expr, dict]:
	"""Handle: x and y, x or y (simplified - both sides always evaluated)."""

	captures = {}
	evaluated = []

	for value in node.values:
		if isinstance(value, ast.Compare):
			# Nested comparison: use our comparison handler
			expr, expr_captures = self.visit_Compare(value)
		else:
			# Simple value: capture it
			var = self.fresh_var()
			self.statements.append(ast.Assign([ast.Name(var, ast.Store())], value))
			expr = ast.Name(var, ast.Load())
			expr_captures = {var: value}

		evaluated.append(expr)
		captures.update(expr_captures)

	return ast.BoolOp(node.op, evaluated), captures
```

Trade-off: This evaluates both sides of and/or, which is different from Python's short-circuit semantics. However:

    It doesn't break correctness (no side effects in most test assertions)
    It's much simpler than pytest's nested If statement approach
    It still captures all the values you need for debugging

Related pytest code: See visit_BoolOp() in src/_pytest/assertion/rewrite.py:985-1040

Pytest's version generates nested If statements to respect Python's short-circuit evaluation (lines 1000-1035). This is the primary source of complexity.

### 4. The Main Handler: visit_Assert()

This is where everything comes together:
```python
def visit_Assert(self, node: ast.Assert) -> list[ast.stmt]:
	"""
	Replace:   assert x == y
	With:      @py_assert0 = x
	          @py_assert1 = y
	          if not (@py_assert0 == @py_assert1):
	              msg = _build_assertion_message(...)
	              raise AssertionError(msg)
	"""
	self.statements = []
	self.var_counter = 0

	# Rewrite the test expression based on its type
	if isinstance(node.test, ast.Compare):
		condition, captures = self.visit_Compare(node.test)
	elif isinstance(node.test, ast.BoolOp):
		condition, captures = self.visit_BoolOp(node.test)
	else:
		# Fallback: capture the whole expression
		var = self.fresh_var()
		self.statements.append(ast.Assign([ast.Name(var, ast.Store())], node.test))
		condition = ast.Name(var, ast.Load())
		captures = {var: node.test}

	# Build the if statement with error message
	negation = ast.UnaryOp(ast.Not(), condition)

	# Call runtime message builder
	msg_var = self.fresh_var()
	self.statements.append(
		ast.Assign(
			[ast.Name(msg_var, ast.Store())],
			ast.Call(
				ast.Name("_build_assertion_message", ast.Load()),
				[
					ast.Constant(ast.unparse(node.test)),  # Original text
					ast.Dict(
						keys=[ast.Constant(k) for k in captures.keys()],
						values=[
							ast.Call(
								ast.Name("repr", ast.Load()),
								[ast.Name(k, ast.Load())],
								[],
							)
							for k in captures.keys()
						],
					),
				],
				[],
			),
		)
	)

	# Create the raise statement
	raise_stmt = ast.Raise(
		ast.Call(
			ast.Name("AssertionError", ast.Load()), [ast.Name(msg_var, ast.Load())], []
		)
	)

	# Create the if statement
	if_stmt = ast.If(negation, [msg_build, raise_stmt], [])

	self.statements.append(if_stmt)
	return self.statements
```
Related pytest code: See visit_Assert() in src/_pytest/assertion/rewrite.py:820-939

Key differences from pytest:

    We call a runtime _build_assertion_message() function (simpler than format context stack)
    No expl_stmts tracking (no nested expression explanation building)
    No handling for walrus operators or assertion pass hooks (lines 941-952)

### 5. Runtime Message Builder

The message is built at test runtime, not rewrite time:
```python
def _build_assertion_message(assertion_text: str, values: dict[str, str]) -> str:
	"""Format the assertion error message from captured values."""
	msg = f"assert {assertion_text}"

	if values:
		msg += "\n  where:"
		for name, repr_value in sorted(values.items()):
			# Strip the @py_assert prefix for readability
			display_name = name.replace("@py_assert", "x")
			msg += f"\n    {display_name} = {repr_value}"

	return msg
```
Example output:
```

AssertionError: assert x == y
  where:
    x0 = 4
    x1 = 5
```
Related pytest code: See format_explanation() in src/_pytest/assertion/util.py:41-53

Pytest's version parses a special mini-language with escape sequences like \n{, \n}, and \n~ for nested explanations. Our version is simpler.
## Integration Points
### Using the Rewriter Without an Import Hook

The simplest integration: rewrite test files explicitly:
```python

def rewrite_test_file(filename: str):
    """Read a test file, rewrite asserts, return compiled code."""
    with open(filename) as f:
        source = f.read()

    tree = ast.parse(source)
    rewriter = SimpleAssertRewriter()

    # Rewrite all asserts at module level
    new_body = []
    for node in tree.body:
        if isinstance(node, ast.Assert):
            new_body.extend(rewriter.visit_Assert(node))
        else:
            new_body.append(node)

    tree.body = new_body

    # Add the message builder function to the module
    tree.body.insert(0, ast.FunctionDef(
        name="_build_assertion_message",
        args=ast.arguments(
            posonlyargs=[],
            args=[ast.arg("assertion_text"), ast.arg("values")],
            kwonlyargs=[],
            kw_defaults=[],
            defaults=[]
        ),
        body=[/* implementation */],
        decorator_list=[]
    ))

    return compile(tree, filename, "exec")
```
### With an Import Hook (Optional)

If you want automatic rewriting on import (like pytest does), use PEP 302:
```python
import importlib.abc
import importlib.machinery
import sys


class AssertRewritingHook(importlib.abc.MetaPathFinder, importlib.abc.Loader):
	def find_spec(self, name, path, target=None):
		# Only rewrite test_*.py files
		if not name.startswith("test_"):
			return None
		# ... return a spec pointing to this loader

	def exec_module(self, module):
		# Read source, rewrite, compile, and execute
		source = pathlib.Path(module.__spec__.origin).read_bytes()
		tree = ast.parse(source)
		SimpleAssertRewriter().rewrite_module(tree)
		code = compile(tree, module.__spec__.origin, "exec")
		exec(code, module.__dict__)


sys.meta_path.insert(0, AssertRewritingHook())
```

Related pytest code: See AssertionRewritingHook in src/_pytest/assertion/rewrite.py:67-289

Pytest's version handles:

    Caching rewritten bytecode (.pyc files) - lines 163-179
    Configuration for which files to rewrite - lines 220-239
    Concurrent write safety - lines 79-81, 172-176

## Comparison with Pytest
Feature	Simple Version	Pytest
Code size	~300 lines	~1200 lines
Comparison handling	✅ Full	✅ Full
Boolean operators	⚠️ Works (no short-circuit)	✅ Perfect
Walrus operators (:=)	❌ Not handled	✅ Full
Message formatting	Simple strings	Mini-language + stack
Import hook	Optional	Built-in
Bytecode caching	None	Yes
Call result display	Basic	Detailed
Attribute access chaining	Basic	Detailed

## When to Use Each Approach
Use this simple version if:

    You're building a custom testing framework
    You want assertion introspection without complexity
    Your tests mostly use comparisons
    You don't need production-grade caching
    You're learning how assertion rewriting works

Use pytest's approach if:

    You need perfect Python semantics
    You have many tests with complex boolean logic
    You want bytecode caching for performance
    You need to hook into the import system
    You need all the built-in pytest features

## Testing Your Implementation
```python
def test_simple_comparison():
	"""Test that we capture both sides of a comparison."""

	def assert_equal(a, b):
		# Your rewritten assertion
		pass

	try:
		assert_equal(4, 5)
		assert False, "Should have raised"
	except AssertionError as e:
		error_msg = str(e)
		assert "4" in error_msg
		assert "5" in error_msg
		print(f"✓ Got message: {error_msg}")


def test_complex_comparison():
	"""Test chained comparisons."""
	x, y, z = 1, 2, 3

	# Your rewriter should show all three values
	try:
		# assert x > y > z  (would fail here)
		pass
	except AssertionError as e:
		error_msg = str(e)
		assert "1" in error_msg
		assert "2" in error_msg
		assert "3" in error_msg
```

## Further Reading

    Pytest's assertion rewriting: src/_pytest/assertion/rewrite.py
    Pytest's assertion utilities: src/_pytest/assertion/util.py
    PEP 302 (Import Hooks): https://www.python.org/dev/peps/pep-0302/
    AST module documentation: https://docs.python.org/3/library/ast.html
    Pytest's blog post: http://pybites.blogspot.be/2011/07/behind-scenes-of-pytests-new-assertion.html

## Summary

Building assertion rewriting is achievable without enterprise-grade complexity. By focusing on:

    Comparisons (the common case)
    Simple boolean operators (acceptable trade-offs)
    Runtime message building (simpler than format stacks)
    Skipping edge cases (walrus, short-circuit optimization)

You can get 80% of pytest's value in 25% of the code. For most testing frameworks, this is the right trade-off.
