from __future__ import annotations
from typing import Iterable, IO, Callable, Iterator, cast
from typing_extensions import Self, Type, TypeVar, Never


class Renderable:
    priority: int = 0
    associativity = "both"

    def stream(self, context: Context) -> TokenStream:
        return NotImplemented

    def wrap(self) -> Renderable:
        """
        This method should return a version of Renderable that retains the same meaning but has higher priority.
        For example, if your renderable is a Python expression `a + b`, this method should return `(a + b)`

        By default, it wraps in parens `x` -> `(x)`
        """
        return Parens(self)

    def priority_comparator(
        self,
        operation: Renderable,
        side: str = "none",
    ) -> bool:
        """Used to decide if the expression should be wrapped to preserve priority and associativity rules."""
        if self.priority < operation.priority:
            return True

        if self.priority == operation.priority:
            if side == "none" or self.associativity == "both":
                return False
            if self.associativity != side:  # e.g "left" != "right" and vice versa
                return True

        return False

    def respect_priority(
        self,
        operation: Renderable,
        comparator: Comparator | None = None,
        side: str = "none",
    ) -> Renderable:
        """
        This method should be called to avoid breaking priority in complex expressions.

        It should be called from parent expression __init__

        `operation` is the object of parent expression (operation)
        `comparator` is a function that should return True if the expression should be wrapped.
        If no comparator is passed, `self.priority_comparator` is used as comparator.

        `side` is a parameter denoting the side of `self` in the expression to support associativity (or any other side-specific behaviour).
        This is mostly arbitrary, but the basic convention is to use "left" and "right" for binary expression, and "none" as default.
        """

        if not comparator:

            def default_comparator(self: Renderable, operation: Renderable, side: str):
                return self.priority_comparator(operation, side)

            comparator = default_comparator

        if comparator(self, operation, side):
            return self.wrap()

        return self

    def render_string(self, context: Payload | None = None):
        """Render component with a provided context. Check `Renderer` class for advanced rendering"""
        return Renderer(context).render_string(self)


class Marker:
    def __init__(self, key: str, data: Payload):
        self.key = key
        self.data = {k: data[k] for k in sorted(data)}

    def __hash__(self) -> int:
        return hash((self.key, tuple(self.data.items())))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Marker):
            return False

        return self.key == other.key and self.data == other.data


_T = TypeVar("_T", str, bytes)


class StreamFile(IO[_T]):
    def __init__(self, stream: Iterable[_T], cls: Type[_T]):
        self.stream: Iterator[_T] = iter(stream)
        self.empty: _T = cls()

        self.newline: _T

        if isinstance(self.empty, bytes):
            self.newline = cast(_T, b"\n")
        else:
            self.newline = cast(_T, "\n")

        self.buffer: _T = self.empty

    def get_next(self) -> _T | None:
        if self.buffer:
            return self.store()
        return next(self.stream, None)

    def store(self, item: _T | None = None) -> _T:
        prev = self.buffer

        if item is None:
            item = self.empty

        self.buffer = item
        return prev

    def join(self, buf: Iterable[_T]) -> _T:
        return self.empty.join(buf)

    def read(self, __n: int = -1) -> _T:
        local_buffer: list[_T] = []
        remaining = __n

        if __n < 0:
            return self.join(self.stream)

        if not __n:
            return self.empty

        while remaining >= 0:
            elem = self.get_next()

            if elem is None:
                break

            if not elem:
                continue  # no need to join empty strings

            elem_length = len(elem)

            if elem_length < remaining:
                local_buffer.append(elem)
            else:
                local_buffer.append(elem[:remaining])
                self.store(elem[remaining:])
                break

            remaining -= elem_length

        return self.join(local_buffer)

    def readlines(self, __hint: int = -1) -> list[_T]:
        buf: list[_T] = []

        if __hint < 0:
            return cast(list[_T], self.read().split(self.newline))

        for _ in range(__hint):
            line = self.readline()
            if not line:
                break

        return buf

    def readline(self, __limit: int = -1) -> _T:
        linebuf: list[_T] = []

        while True:
            next_piece = self.get_next()

            if not next_piece:
                break

            if self.newline in next_piece:
                start, end = cast(list[_T], next_piece.split(self.newline))
                linebuf.append(start)
                self.store(end)
                linebuf.append(self.newline)
                break

        return self.join(linebuf)

    @property
    def mode(self) -> str:
        if isinstance(self.empty, bytes):
            return "rb"
        return "b"

    @property
    def name(self) -> str:
        return ""

    def close(self) -> None:
        pass

    @property
    def closed(self) -> bool:
        return False

    def fileno(self) -> int:
        return 0

    def flush(self) -> None:
        pass

    def isatty(self) -> bool:
        return False

    def readable(self) -> bool:
        return True

    def seek(self, offset: int, whence: int = 0) -> Never:
        raise TypeError("stream file doesn't support seek")

    def seekable(self) -> bool:
        return False

    def tell(self) -> int:
        return 0

    def truncate(self, size: int | None = None) -> Never:
        raise TypeError("stream file cannot be truncated")

    def writable(self) -> bool:
        return False

    def write(self, s: _T) -> Never:
        raise TypeError("stream file is not writable")

    def writelines(self, lines: Iterable[_T]) -> Never:
        raise TypeError("stream file is not writable")

    def __enter__(self) -> Self:
        return self

    def __exit__(self, type, value, traceback) -> None:
        pass

    def __iter__(self):
        while True:
            next_line = self.readline()

            if not next_line:
                return

            yield next_line

    def __next__(self):
        return self.readline()


class Renderer:
    def __init__(self, context: Payload | None = None):
        self.context = context or {}

    def get_subrenderer(self, local_context: Payload) -> Renderer:
        return Renderer(
            {
                **self.context,
                **local_context,
            }
        )

    def stream(
        self, renderable: Renderable, local_context: Payload | None = None
    ) -> TokenStream:
        if local_context:
            sub_renderer = self.get_subrenderer(local_context)
            return sub_renderer.stream(renderable)

        return renderable.stream(Context(self))

    def byte_stream(
        self, renderable: Renderable, local_context: Payload | None = None
    ) -> ByteStream:
        for token in self.str_stream(renderable, local_context):
            yield token.encode("utf-8")

    def str_stream(
        self, renderable: Renderable, local_context: Payload | None = None
    ) -> StrStream:
        for token in self.stream(renderable, local_context):
            if isinstance(token, str):
                yield token

    def render_bytes(
        self, renderable: Renderable, local_context: Payload | None = None
    ):
        return b"".join(
            self.byte_stream(
                renderable,
                local_context,
            )
        )

    def render_string(
        self, renderable: Renderable, local_context: Payload | None = None
    ) -> str:
        return "".join(
            self.str_stream(
                renderable,
                local_context,
            )
        )

    def as_file(
        self, renderable: Renderable, local_context: Payload | None = None
    ) -> IO[str]:
        return StreamFile(
            self.str_stream(
                renderable,
                local_context,
            ),
            str,
        )

    def as_binary_file(
        self, renderable: Renderable, local_context: Payload | None = None
    ) -> IO[bytes]:
        return StreamFile(
            self.byte_stream(
                renderable,
                local_context,
            ),
            bytes,
        )


class Context:
    def __init__(self, renderer: Renderer):
        self._renderer = renderer

    def __getattr__(self, __name: str) -> object:
        return self._renderer.context.get(__name)

    def __setattr__(self, __name: str, __value: object) -> None:
        if __name == "_renderer":
            return super().__setattr__(__name, __value)
        self._renderer.context[__name] = __value

    def derive(self, **kwargs: object):
        return Context(
            self._renderer.get_subrenderer(kwargs),
        )


def get_render(context: Context) -> Callable[[Renderable], TokenStream]:
    return lambda r: r.stream(context)


from .internal_types import (
    ByteStream,
    Comparator,
    Payload,
    StrStream,
    TokenStream,
)

from .startkit import Parens

_RT = TypeVar("_RT", bound=Renderable)
