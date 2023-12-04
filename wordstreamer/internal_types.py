from typing import (
    Callable,
    Dict,
    Iterable,
    Tuple,
    TypeVar,
    Union,
)


Piece = TypeVar("Piece", bytes, str, "Token")

Token = Union[str, "Marker"]

Stream = Iterable[Piece]
TokenStream = Stream[Token]
StrStream = Stream[str]
ByteStream = Stream[bytes]

StreamTransformer = Callable[[Stream], Stream]

Payload = Dict[str, object]

Comparator = Callable[["Renderable", "Renderable", str], bool]
ParenSet = Tuple[Token, Token]

from .core import Marker, Renderable
