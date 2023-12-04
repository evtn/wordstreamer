# Building blocks for a simple math expression language, including a correct priority system.

from __future__ import annotations

from wordstreamer import Renderable, Context, TokenStream


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

    def __neg__(self) -> UnaryMinus:
        return UnaryMinus(self)


class Number(Expression):
    priority = 100

    def __init__(self, value: float):
        self.value = value

    def stream(self, context: Context) -> TokenStream:
        yield str(self.value)


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

    def priority_comparator(self, operation: Renderable, side: str = "none") -> bool:
        if side == "right":
            return False

        return super().priority_comparator(operation, side)

    def stream(self, context: Context) -> TokenStream:
        yield "-"
        yield from self.rhs.stream(context)


def number(value: float) -> Number | UnaryMinus:
    if value < 0:
        return -Number(abs(value))
    return Number(value)


expression = number(6) + number(10) * (number(4.4) ** number(-5)) ** number(4)

print(expression.render_string())
