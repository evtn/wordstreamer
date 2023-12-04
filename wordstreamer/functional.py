from __future__ import annotations
from typing import Callable, Concatenate, ParamSpec

from .core import Renderable

FuncArgs = ParamSpec("FuncArgs")


class FunctionalRenderable(Renderable):
    def __init__(self, renderer: Callable[[Context], TokenStream]):
        self.renderer = renderer

    def stream(self, context: Context) -> TokenStream:
        yield from self.renderer(context)


def make_renderable(func: Callable[Concatenate[Context, FuncArgs], TokenStream]):
    def call(*args: FuncArgs.args, **kwargs: FuncArgs.kwargs) -> FunctionalRenderable:
        renderable = FunctionalRenderable(
            lambda context: func(context, *args, **kwargs)
        )
        return renderable

    return call


from .core import Context
from .internal_types import TokenStream
