from typing import (
    Any,
    Callable,
    Dict,
    Iterable,
    Tuple,
    TypeVar,
    Union,
)


Piece = TypeVar("Piece", bound=Union[bytes, str, "Token"])

Token = Union[str, "Marker"]

Stream = Iterable[Piece]
TokenStream = Stream[Token]
StrStream = Stream[str]
ByteStream = Stream[bytes]

StreamTransformer = Callable[[Stream], Stream]

Payload = Dict[str, Any]

Comparator = Callable[["Renderable", "Renderable", str], bool]
ParenSet = Tuple[Token, Token]

from .core import Marker, Renderable
