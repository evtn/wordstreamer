from __future__ import annotations

from .stream_utils import add_tab, separated
from .core import Context, Renderable, get_render
from .internal_types import StreamTransformer, Token, TokenStream


class Parens(Renderable):
    """Generic wrapper"""

    def __init__(
        self, contents: Renderable, open_paren: Token = "(", close_paren: Token = ")"
    ):
        self.contents = contents
        self.parens = (open_paren, close_paren)

    def wrap(self):
        return self

    def render_parts(self, context: Context) -> TokenStream:
        yield from self.contents.stream(context)

    def stream(self, context: Context) -> TokenStream:
        yield self.parens[0]
        yield from self.render_parts(context)
        yield self.parens[1]


class Separated(Renderable):
    """Base block to render a sequence of renderables separated by some separator"""

    def __init__(
        self, *renderables: Renderable, separator: TokenStream, trail: bool = False
    ):
        self.renderables = renderables
        self.separator = separator
        self.trail = trail

    def stream(self, context: Context) -> TokenStream:
        render = get_render(context)
        return separated(
            *map(render, self.renderables),
            separator=self.separator,
            trail=self.trail,
        )


class Block(Renderable):
    def __init__(
        self,
        head: Renderable | None,
        body: Renderable,
        wrapper: StreamTransformer | None = None,
        indenter: StreamTransformer | None = None,
    ) -> None:
        self.head = head
        self.body = body
        self.wrapper: StreamTransformer = wrapper or self.default_wrap
        self.indenter: StreamTransformer = indenter or add_tab

    def default_wrap(self, stream: TokenStream) -> TokenStream:
        yield "{"
        yield " "
        yield "\n"
        yield from stream
        yield "\n"
        yield "}"

    def stream(self, context: Context):
        if self.head:
            yield from self.head.stream(context)

        yield from self.wrapper(self.indenter(self.body.stream(context)))


class Stringify(Renderable):
    def __init__(self, contents: object):
        self.contents = contents

    def stream(self, context: Context) -> TokenStream:
        yield str(self.contents)
