from wordstreamer import Renderable
from wordstreamer.core import Context, Renderer
from wordstreamer.internal_types import TokenStream
from wordstreamer.startkit import Parens, Separated


class Chars(Renderable):
    def __init__(self, text: str):
        self.text = text

    def stream(self, context: Context) -> TokenStream:
        yield from self.text


class ContextAware(Renderable):
    def stream(self, context: Context) -> TokenStream:
        yield str(context.test or "what")

        if context.is_funny:
            yield ")"


class TestClass:
    def test_renderable(self):
        s = "test123"

        literal = Chars(s)
        renderer = Renderer()

        assert renderer.render_string(literal) == s
        assert renderer.render_bytes(literal) == s.encode()

        assert list(renderer.stream(literal)) == list(s)
        assert list(renderer.str_stream(literal)) == list(s)
        assert list(renderer.byte_stream(literal)) == [c.encode("utf-8") for c in s]

    def test_contextual(self):
        ca = ContextAware()

        assert ca.render_string() == "what"
        assert ca.render_string({"test": 123}) == "123"
        assert ca.render_string({"is_funny": True}) == "what)"
        assert ca.render_string({"test": 2384, "is_funny": True}) == "2384)"

    def test_wrap(self):
        parts_data: list[int | str] = [*"test", 1, 2, 3]
        parts = [Chars(str(x)) for x in parts_data]

        parens = Parens(Separated(*parts, separator=[", "]))

        assert parens.render_string() == f"({', '.join(map(str, parts_data))})"
