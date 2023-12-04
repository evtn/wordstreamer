from __future__ import annotations

"""

An almost correct implementation of Python's json.dumps function.
For clarity, this example does not implement:

- Invalid key skipping (`skipkeys` is always false)
- Circular reference check (`check_circular` is always false)
- NaN and Infinity handling (those are inserted as-is, check `JSONLiteral.stream`)
- Default value function

What IS implemented:

- Full default JSON type set (number, boolean, string, null, objects and arrays)
- Rendering with or without `ensure_ascii`
- String escaping
- Customizable item/key separators
- Pretty printing (with indent)
"""

from typing import Dict, Iterable, List, Sequence, Union
from wordstreamer import Renderable, Context, TokenStream, Renderer
from wordstreamer.internal_types import Token
from wordstreamer.stream_utils import add_tab, separated
from wordstreamer.utils import get_default

common_escapes = {
    "\b": "\\b",
    "\f": "\\f",
    "\n": "\\n",
    "\r": "\\r",
    "\t": "\\t",
    '"': '\\"',
}


def encode_utf16(char: str) -> str:
    bs = char.encode("utf-16")[2:]

    parts = bs[:2], bs[2:]

    return "".join(escape_char(int(part[::-1], 16)) for part in parts)


def escape_char(value: int):
    return f"\\u{value:04x}"


def json_escape_inner(s: str, ensure_ascii: bool) -> Iterable[str]:
    for char in s:
        if char in common_escapes:
            yield common_escapes[char]
            continue

        charcode = ord(char)

        if charcode > 0xFFFF:
            yield encode_utf16(char)

        elif charcode < 32 or (ord(char) > 127 and ensure_ascii):
            yield escape_char(charcode)

        else:
            yield char


def json_escape(s: str, context: Context):
    return "".join(json_escape_inner(s, get_default(context.ensure_ascii, True)))


class JSONValue(Renderable):
    def get_indent(self, context: Context) -> str | None:
        indent_setting = context.indent

        if indent_setting is None:
            return

        if isinstance(indent_setting, int):
            indent_setting = max(0, indent_setting)
            return indent_setting * " "

        if isinstance(indent_setting, str):
            return indent_setting

        return

    def get_separator(self, context: Context) -> list[Token]:
        indent = self.get_indent(context)

        base_separator = context.item_separator
        separator: list[Token] = []

        if base_separator is None:
            separator.append(",")
            if indent is None:
                separator.append(" ")
        else:
            separator.append(base_separator)

        if indent is not None:
            separator.append("\n")

        return separator

    def get_key_separator(self, context: Context) -> list[Token]:
        base_separator = context.key_separator
        separator: list[Token] = []

        if base_separator is None:
            separator.append(":")
            separator.append(" ")
        else:
            separator.append(base_separator)

        return separator


class JSONLiteral(JSONValue):
    def __init__(self, value: float | str | None):
        self.value = value

    def stream(self, context: Context) -> TokenStream:
        if isinstance(self.value, bool):
            yield str(self.value).lower()
            return

        if self.value is None:
            yield "null"
            return

        if isinstance(self.value, str):
            yield f'"{json_escape(self.value, context)}"'
            return

        yield str(self.value)  # possible improvement: handle nan/inf/-inf


class JSONContainer(JSONValue):
    parens: Sequence[str]

    def render_values(self, context: Context) -> Iterable[TokenStream]:
        return NotImplemented

    def contents(self, context: Context) -> TokenStream:
        indent = self.get_indent(context)

        values_stream = separated(
            *self.render_values(context), separator=self.get_separator(context)
        )

        if indent is None:
            yield from values_stream
        else:
            yield "\n"
            yield from add_tab(values_stream, tab_char=indent)
            yield "\n"

    def stream(self, context: Context) -> TokenStream:
        yield self.parens[0]
        yield from self.contents(context)
        yield self.parens[1]


class JSONObject(JSONContainer):
    parens = "{}"

    def __init__(self, value: dict[str, JSONValue]):
        self.value = value

    def render_key(self, key: str, context: Context):
        yield from JSONLiteral(key).stream(context)
        yield from self.get_key_separator(context)
        yield from self.value[key].stream(context)

    def render_values(self, context: Context) -> Iterable[TokenStream]:
        for key in self.value:
            yield self.render_key(key, context)


class JSONArray(JSONContainer):
    parens = "[]"

    def __init__(self, value: list[JSONValue]):
        self.value = value

    def render_values(self, context: Context) -> Iterable[TokenStream]:
        for value in self.value:
            yield value.stream(context)


JSONType = Union[Dict[str, "JSONType"], List["JSONType"], str, float, None]


def dumps(
    obj: JSONType,
    *,
    ensure_ascii: bool = True,
    indent: int | str | None = None,
    separators: tuple[str, str] | None = None,
) -> str:
    renderer = Renderer(
        {
            "ensure_ascii": ensure_ascii,
            "indent": indent,
            "separator": separators[0] if separators else None,
            "key_separator": separators[1] if separators else None,
        }
    )

    renderable = to_renderable(obj)

    return renderer.render_string(renderable)


def to_renderable(obj: JSONType) -> JSONValue:
    if obj is None:
        return JSONLiteral(None)

    if isinstance(obj, (float, int, str)):
        return JSONLiteral(obj)

    if isinstance(obj, dict):
        return JSONObject(
            {
                key: to_renderable(
                    value,
                )
                for key, value in obj.items()
            }
        )

    if isinstance(obj, list):
        return JSONArray(
            [
                to_renderable(
                    elem,
                )
                for elem in obj
            ]
        )

    raise TypeError(f"invalid type for json: {type(obj)}")
