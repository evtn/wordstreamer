from __future__ import annotations
from typing import TypeVar
from typing_extensions import TypeGuard


_T = TypeVar("_T")


def get_default(cond: _T | None, default: _T, value: _T | None = None) -> _T:
    """
    Returns default if cond is None.
    If cond is not None, returns value if it's also not None, else returns cond.

    Two-arg form
    ```python
    get_default(cond, default)
    ```
    is equivalent to

    ```python
    default if cond is None else cond
    ```

    Three-arg form
    ```python
    get_default(cond, default, value)
    ```
    is equivalent to

    ```python
    default if cond is None else value
    ```
    """

    if cond is None:
        return default

    return get_default(value, cond)


def is_marker(token: Token) -> TypeGuard[Marker]:
    return isinstance(token, Marker)


from .core import Marker
from .internal_types import Token
