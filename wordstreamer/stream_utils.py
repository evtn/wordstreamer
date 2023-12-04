from __future__ import annotations
from collections import deque


def add_tab(
    stream: Stream[Token], tab_char: str = "    ", newlines: set[Token] | None = None
) -> Stream[Token]:
    """

    Adds `tab_char` after any token that is equal to any of the newline tokens in `newlines`.

    By default, `tab_char` is "    " (4 ASCII spaces U+0020) and `newlines` is {"\\n"}

    """

    newlines = get_default(newlines, {"\n"})

    yield tab_char

    for token in stream:
        yield token

        if token in newlines:
            yield tab_char


def separated(
    *streams: Stream[Piece], separator: Stream[Piece], trail: bool = False
) -> Stream[Piece]:
    """
    Interjects `separator` tokens between streams, outputting a new chained stream.

    `trail` defines if separator should be added after last token, i.e. if a trailing comma should be inserted
    """

    separator_list = list(
        separator
    )  # separator needs to be stored because it could be a one-time stream

    for i, stream in enumerate(streams):
        yield from stream
        if trail or i + 1 != len(streams):
            yield from separator_list


def prepend(stream: Stream[Piece], *pieces: Piece) -> Stream[Piece]:
    """Injects tokens before stream"""
    return concat(pieces, stream)


def append(stream: Stream[Piece], *pieces: Piece) -> Stream[Piece]:
    """Injects tokens after stream"""
    return concat(stream, pieces)


def omit_start(stream: Stream[Piece], count: int = 1) -> Stream[Piece]:
    """Omits `count` tokens from the start of the stream"""
    for token in stream:
        if count > 0:
            count -= 1
            continue

        yield token


def omit_end(stream: Stream[Piece], count: int = 1) -> Stream[Piece]:
    """Omits `count` tokens from the end of the stream"""
    buf: deque[Piece] = deque()

    for token in stream:
        buf.append(token)

        if len(buf) > count:
            yield buf.popleft()


def concat(*streams: Stream[Piece] | None) -> Stream[Piece]:
    """Concatenates several streams"""
    for stream in streams:
        if not stream:
            continue
        yield from stream


def wrap(
    stream: Stream[Piece],
    prefix: Stream[Piece],
    postfix: Stream[Piece],
) -> Stream[Piece]:
    """Prepends `prefix` before stream and appends `postfix` after stream"""

    return concat(prefix, stream, postfix)


def stream_noop(stream: Stream[Piece]) -> Stream[Piece]:
    return stream


from .internal_types import Piece, Stream, Token
from .utils import get_default
