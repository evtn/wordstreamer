wordstreamer is a tiny generic text-generation module. It is a set of convenient generator-based tools to generate any text.  
Be it code, markup or anything else, wordstreamer got you covered.

Streams / generators are perfect for text generations.  
Those are easy to use, easily combined, and have a great speed and memory footprint in concurrent / stream-based workflows (such as webservers).

Features:

1. Build custom renderables

    - An operation priority system with optional custom wrapping logic
    - Render as string / bytes, as string / byte streams or as text / binary files
    - Insert arbitrary markers to pass information upstream
    - Use context to tweak rendering as you need
    - Several common generic renderables included in startkit

2. Build custom stream processors

    - Process streams of tokens in any way
    - Several common processors included in stream_utils

3. Have fun with strings attached

# Installation

Just install `wordstreamer` module from PyPI

# Examples

Check out [examples](https://github.com/evtn/wordstreamer/blob/lord/examples/) folder for examples

[Math expressions](https://github.com/evtn/wordstreamer/blob/lord/examples/math.py)
[Almost correct json.dumps implementation](https://github.com/evtn/wordstreamer/blob/lord/examples/json.py)

# Docs

## Core

Core module (`wordstreamer.core`) consists of several user-facing entities: `Renderable` base class, `Marker` and `Renderer` classes and `get_render` function.  
Other classes (`Context` and `StreamFile`) are internal, but fairly easy to use if needed.

Your basic flow is:

-   Create severable `Renderable` for your needs
-   Create an instance of `Renderer` with context payload
-   Use one of `Renderer`'s methods to output the renderable in preferrable format

### Renderable

`wordstreamer.core.Renderable` is the main class of the module.

Your basic custom renderable has to implement `stream` method that would return a stream of tokens.

Here's a simple renderable that renders a list-like string from a range, simulating `str(list(range(...)))`

```python
from typing import Iterable
from wordstreamer import Renderable, Context, TokenStream
from wordstreamer.stream_utils import omit_end


class Range(Renderable):
    def __init__(self, value: range):
        self.value = value

    # let's make a separate method for convenience
    def numbers(self, context: Context) -> TokenStream:
        for n in self.value:
            yield str(n)
            yield ","
            yield " "

    def stream(self, context: Context) -> TokenStream:
        yield "["
        yield from omit_end(self.numbers(context))
        yield "]"

```

(Note: we could have done `yield ", "`, but that would make stream manipulation less effective (e.g. stripping unwanted spaces))

Then, to render it, use `render_string`:

```python
# prints "[2, 4, 6, 8]"
print(
    Range(range(2, 9, 2)).render_string()
)
```

### Functional renderables

Sometimes, you need simple renderables defining only `.stream()` method, similar to React functional components.

Something like this:

```python
def render_sum(left: float, right: float) -> TokenStream:
    yield str(left)
    yield " + "
    yield str(right)
```

wordstreamer defines a convenience wrapper for that, `make_renderable`.

Just use it as a decorator and add `Context` as a first positional argument:

```python
from wordstreamer import make_renderable, Context

@make_renderable
def render_sum(context: Context, left: float, right: float) -> TokenStream:
    yield str(left)
    yield " + "
    yield str(right)
```

And use it like any other renderable, omitting `context` argument:

```python
print(
    render_sum(4, 5).render_string()
)
```

The downside of that approach is that you get a basic plain Renderable, which makes it impossible to build a complex type hierarchy

### Renderer and Context

While using `renderable.render_string()` is totally fine, you can easily dive into the rendering flow.

You have noticed this mysterious Context value going inside function arguments. This is a payload that allows you to pass data from top to bottom, and vice versa.  
It can be passed into `renderable.render_string(context: Payload)`, where `Payload` is a dictionary with `str` keys and arbitrary values.

Inside `.stream` functions, this payload becomes an instance of `Context`, which is a simple wrapper that supports attribute access:

```python

class MyRenderable(Renderable):
    def stream(self, context: Context) -> TokenStream:
        if context.left:
            yield str(context.left)

        if context.op:
            yield str(context.op)

        if context.right:
            yield str(context.right)


MyRenderable().render_string({"left": 4, "op": "+", "right": 5}) # "4+5"
```

Context is also mutable and _derivable_. It means you can derive a new context from an old one and a new payload, passing it to bottom components:

```python
...

def stream(self, context: Context) -> TokenStream:
    level = context.level or 0

    subcontext = context.derive(level=level + 1)
    yield "-" * level
    yield from self.child.render(subcontext)
...
```

When you need a more granular control over rendering steps and output, use `Renderer` class. Let's start with `Renderable.render_str` source code:

```python
def render_string(self, context: Payload | None = None):
    """Render component with a provided context. Check `Renderer` class for advanced rendering"""
    return Renderer(context).render_string(self)
```

Oh no, we were fooled! Anyway, the `Renderer` class takes care of transforming the token stream into some other form, be it a string, bytestring, or even a file.

To use it, first create a renderer:

```python
from wordstreamer import Renderer

renderer = Renderer({"some_key": 1, "another_key": "secret_passwordQWERTY"})

```

Then, you can produce the output in 7 formats:

-   As a `Stream[Token]` with `renderer.stream(payload)`
-   As a `Stream[str]` with `renderer.str_stream(payload)` (takes a TokenStream and drops all `Marker` instances)
-   As a `Stream[bytes]` with `renderer.byte_stream(payload)` (takes a Stream[str] and encodes in as UTF-8)
-   As `bytes` with `renderer.render_bytes(payload)` (joins a `Stream[bytes]`)
-   As `str` with `renderer.render_string(payload)` (joins a `Stream[str]`)
-   As a text file with `renderer.as_file(payload)` (makes a file wrapper around `Stream[str]`)
-   As a binary file with `renderer.as_binary_file(payload)` (makes a file wrapper around `Stream[bytes]`)

## Combining renderables

Any complex text builder has nesting.

Due to stream-based flow, one can easily combine renderables.

Let's make a simple math expression renderer. We will support numbers, five binary operations (`+`, `-`, `*`, `/`, and `**`), and unary `-`.

First, let's make a base class to:

-   define common methods
-   build a type hierarchy (this is optional, but it's extremely convenient and straightforward when you have a complex syntax).

```python
from __future__ import annotations

from wordstreamer import Renderable

# we will need this later
priorities: dict[str, int] = {
    "+": 0,
    "-": 0,
    "*": 1,
    "/": 1,
    "u-": 2,
    "**": 3,
}


class Expression(Renderable):
    def __add__(self, other: Expression) -> BinaryExpression:
        return BinaryExpression(self, "+", other)

    def __sub__(self, other: Expression) -> BinaryExpression:
        return BinaryExpression(self, "-", other)

    def __mul__(self, other: Expression) -> BinaryExpression:
        return BinaryExpression(self, "*", other)

    def __truediv__(self, other: Expression) -> BinaryExpression:
        return BinaryExpression(self, "/", other)

    def __pow__(self, other: Expression) -> BinaryExpression:
        return BinaryExpression(self, "**", other)

    def __neg__(self) -> BinaryExpression:
        return UnaryMinus(self)

```

Then, let's make a renderable for numbers:

```python
class Number(Expression):
    priority = 100

    def __init__(self, value: float):
        self.value = value

    def stream(self, context: Context) -> TokenStream:
        yield str(self.value)
```

And for composite expressions:

```python

class BinaryExpression(Expression):
    associativity = "left"

    def __init__(self, lhs: Expression, op: str, rhs: Expression):
        if op == "**":
            self.associativity = "right"

        self.priority = priorities[op]

        self.lhs = lhs.respect_priority(self, side="left")
        self.rhs = rhs.respect_priority(self, side="right")
        self.op = op

    def stream(self, context: Context) -> TokenStream:
        yield from self.lhs.stream(context)
        yield " "
        yield self.op
        yield " "
        yield from self.rhs.stream(context)


class UnaryMinus(Expression):
    priority = priorities["u-"]

    def __init__(self, rhs: Expression):
        self.rhs = rhs.respect_priority(self)

    # this is an optional tweak to omit parens if the negative expression is on the right side, as in `4 ** -5` but `(-5) ** 4`
    def priority_comparator(self, operation: Renderable, side: str = "none") -> bool:
        if side == "right":
            return False

        return super().priority_comparator(operation, side)

    def stream(self, context: Context) -> TokenStream:
        yield "-"
        yield from self.rhs.stream(context)

```

Finally, we should treat negative numbers the same as a number with an unary minus:

```python

def number(value: float) -> Number | UnaryMinus:
    if value < 0:
        return -Number(abs(value))
    return Number(value)

```

That's it! Now let's test our simple language:

```python
expression = number(6) + number(10) * (number(4.4) ** number(-5)) ** number(4)

# 6 + 10 * (4.4 ** -5) ** 4
print(
    expression.render_string()
)
```

You can find the full code in [examples](https://github.com/evtn/wordstreamer/blob/lord/examples/math.py)

### Priority magic

You may be wondering, where did `()` come from in this example? We didn't render them, right?

Those parens actually come from the `respect_priority` flow.  
We call `expression.respect_priority(operation, comparator, side)` (latter two args are optional), where `expression` is some nested expression, and `operation` is a parent expression.  
In `6 + 5`, the whole expression is operation, while `6` and `5` are sub-expressions.  
In this case, there is no need for wrapping (so that `(6) + (5)` is redundant). But to know that, we have to know **priority rules** of the language.

The default behaviour is simple: having two attributes, `priority` (int), and `associativity` ("left" | "right" | "both").

1. If the sub-expression priority is less than the expression priority, we need wrapping:

```python
e = number(5) + number(6)
e2 = e * number(10)

print(e2.render_string()) # (5 + 6) * 10
```

Here, if we don't wrap, we will get "5 + 6 _ 10", which is not the original intention. But we've defined that `+` priority is `0` and `_`priority is`1`by assigning it in`BinaryExpression` constructor.

So, when we write `s * number(10)`, we do `BinaryExpression(5 + 6, *, 10)`. Let's call this expression `self`

It calls `(5 + 6).respect_priority(self, side="left")`, and, because `(5 + 6)` priority is lower than that of `self`, it wraps.

2. If the priority is the same, default comparator checks the associativity. If the side is "none" or associativity is "both", it doesn't wrap.  
   Then, if side is not the same as associativity, it does wrap, like with `**`:

```python
e = number(5) + number(6)
e2 = number(10) - e

print(e2.render_string()) # 10 - (5 + 6)
```

Despite operations having the same priority, we need to wrap the expression on the right, because otherwise it will become `(10 - 5) + 6` (11), instead of `10 - (5 + 6)` (-1)

---

So, the default behaviour is to adhere to usual binary expression rules, and wrapping with built-in renderable from [**start kit**](#start-kit), Parens.

You can easily customize how wrapping is done by redefining `Renderable.wrap(self) -> Renderable` on your renderable class, without changing the priority behaviour.  
The comparator (`(self, operation, side = "none") -> bool`) can be passed into `.respect_priority`, or you can redefine `.priority_comparator` method

### Markers

Sometimes you may need to pass some data upwards, and for that TokenStream can include instances of Marker, simple data container:

```python
...
def stream(self, context: Context) -> TokenStream:
    yield "[",
    yield Marker("block-content", data={"values": [1, 2, 3]})
    yield "]"
...
```

Then, you can watch for markers upstream, in some parent component:

```python
from wordstreamer.utils import is_marker

...
def stream(self, context: Context) -> TokenStream:
    yield "x"
    yield " "
    yield "="

    for token in self.block.stream(context):
        if is_marker(token) and token.key == "block-content":
            ...
        else:
            yield token
...
```

You can obviously do that with context, but keep in mind that derived context don't pass changes to their parent contexts

## Start Kit and Stream Utils

wordstreamer includes useful building tools in form of two modules: `wordstreamer.startkit` and `wordstreamer.stream_utils`.

The first is a set of common renderables, while the second is a set of functions to manipulate the stream.

### Start Kit

#### Stringify

A simple renderable, taking any object, and rendering it using `str()`:

```python
from wordstreamer.startkit import Stringify

Stringify(6).render_string() # "6"
```

This is useful when injecting pre-rendered content, for fast prototyping, etc.

#### Parens

This is a generic element that wraps your renderable given two strings, one at the start and one at the end.

```python
from wordstreamer.startkit import Parens, Stringify

content = Stringify("content")

Parens(content).render_string() # "(content)"
Parens(content, "[", "]").render_string() # "[content]"
Parens(content, '"', '"').render_string() # '"content"'
```

#### Separated

Renders several renderables, injecting a stream of tokens between every renderable:

```python
from wordstreamer.startkit import Separated, Stringify

numbers = [Stringify(x) for x in range(10)]

Separated(*numbers, separator=[",", " "]).render_string() # "0, 1, 2, 3, 4, 5, 6, 7, 8, 9"
```

If you want to append separator after the stream, pass `trail=True` in the constructor

#### Block

Renders a full-blown block, with full customization.

By default renders a 4-space indented C-style block (with `{}`):

```python
from wordstreamer.startkit import Block, Stringify, Separated
from wordstreamer import (
    Renderable,
    TokenStream,
    make_renderable,
    Context
)

@make_renderable
def counter(context: Context, n: int):
    for i in range(n):
        yield str(i)
        if i + 1 < n:
            yield "\n"

head = Stringify("if 10 == 89")
body = counter(5)

"""
if 10 == 89 {
    0
    1
    2
    3
    4
}
"""
print(
    Block(
        head=head,
        body=body,
    ).render_string()
)
```

But, if you want Python-style, let's do that:

```python
def pythonic_wrapper(stream: TokenStream) -> TokenStream:
    yield ":"
    yield "\n"
    yield from stream
    yield "\n"

"""
if 10 == 89:
    0
    1
    2
    3
    4
"""
print(
    Block(
        head=head,
        body=body,
        wrapper=pythonic_wrapper
    ).render_string()
)
```

You can omit `head` argument altogether, or provide a custom indenter:

```python
def staircase_indenter(stream: TokenStream) -> TokenStream:
    tab_level = 1

    for token in stream:
        yield token
        if token == "\n":
            yield tab_level * 4 * " "
            tab_level += 1

"""
if 10 == 89 {
0
    1
        2
            3
                4
}
"""
print(
    Block(
        head=head,
        body=body,
        indenter=staircase_indenter
    ).render_string()
)
```

### Stream utils

`wordstreamer.stream_utils` contain a set of 'stream transformers' — functions that manipulate stream (or several) building up a new one.

This section is a WIP, but here's what the stream utils module defines:

```python
def add_tab(
    stream: Stream[Token], tab_char: str = "    ", newlines: set[Token] | None = None
) -> Stream[Token]:
    """
    Adds `tab_char` after any token that is equal to any of the newline tokens in `newlines`.

    By default, `tab_char` is "    " (4 ASCII spaces U+0020) and `newlines` is {"\\n"}
    """


def separated(
    *streams: Stream[Piece], separator: Stream[Piece], trail: bool = False
) -> Stream[Piece]:
    """
    Interjects `separator` tokens between streams, outputting a new chained stream.

    `trail` defines if separator should be added after last token, i.e. if a trailing comma should be inserted
    """


def prepend(stream: Stream[Piece], *pieces: Piece) -> Stream[Piece]:
    """Injects tokens before stream"""


def append(stream: Stream[Piece], *pieces: Piece) -> Stream[Piece]:
    """Injects tokens after stream"""


def omit_start(stream: Stream[Piece], count: int = 1) -> Stream[Piece]:
    """Omits `count` tokens from the start of the stream"""


def omit_end(stream: Stream[Piece], count: int = 1) -> Stream[Piece]:
    """Omits `count` tokens from the end of the stream"""


def concat(*streams: Stream[Piece] | None) -> Stream[Piece]:
    """Concatenates several streams"""


def wrap(
    stream: Stream[Piece],
    prefix: Stream[Piece],
    postfix: Stream[Piece],
) -> Stream[Piece]:
    """Prepends `prefix` before stream and appends `postfix` after stream"""


def stream_noop(stream: Stream[Piece]) -> Stream[Piece]:
    """Leaves stream intact, useful to pass as a no-op transformer"""
```
