"""Boolean tag query support for repository rule headers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from search_metadata import RuleHeader, load_rule_headers, visible_in_query


class QueryError(ValueError):
    """Raised when a tag query expression cannot be parsed."""


@dataclass(frozen=True)
class RuleMatch:
    """A rule header matched by a query.

    Args:
        header: Matched rule metadata.
        reason: Human-readable reason the rule matched.
    """

    header: RuleHeader
    reason: str


@dataclass(frozen=True)
class _Token:
    """Token in a Boolean tag expression.

    Args:
        kind: Token category.
        value: Source token value.
    """

    kind: str
    value: str


class _Expression:
    """Evaluable Boolean tag expression node."""

    def matches(self, tags: frozenset[str]) -> bool:
        """Return whether the expression matches a tag set.

        Args:
            tags: Normalized tags for one rule.

        Returns:
            True when the expression matches.
        """
        raise NotImplementedError


@dataclass(frozen=True)
class _Tag(_Expression):
    """Tag lookup expression."""

    tag: str

    def matches(self, tags: frozenset[str]) -> bool:
        """Return whether this tag appears in the given tag set."""
        return self.tag in tags


@dataclass(frozen=True)
class _Not(_Expression):
    """Boolean NOT expression."""

    expr: _Expression

    def matches(self, tags: frozenset[str]) -> bool:
        """Return the negated result for the child expression."""
        return not self.expr.matches(tags)


@dataclass(frozen=True)
class _Binary(_Expression):
    """Boolean binary expression."""

    op: str
    left: _Expression
    right: _Expression

    def matches(self, tags: frozenset[str]) -> bool:
        """Return the AND or OR result for child expressions."""
        if self.op == "AND":
            return self.left.matches(tags) and self.right.matches(tags)
        return self.left.matches(tags) or self.right.matches(tags)


def query_rule_headers(
    root: Path,
    expression: str,
    *,
    include_manual: bool = False,
) -> list[RuleMatch]:
    """Return rule headers matching a Boolean tag expression.

    Args:
        root: Repository root containing ``.rules``.
        expression: Boolean tag expression.
        include_manual: Whether manual-only rules may be returned.

    Returns:
        Sorted matching rule headers.
    """
    parsed = parse_tag_expression(expression)
    headers, _skipped = load_rule_headers(root)
    matches = [
        RuleMatch(header, f"matched tag query: {expression}")
        for header in headers
        if visible_in_query(header, include_manual=include_manual)
        and parsed.matches(frozenset(header.tags))
    ]
    return sorted(matches, key=lambda match: (match.header.name, match.header.path))


def parse_tag_expression(expression: str) -> _Expression:
    """Parse a Boolean tag expression.

    Args:
        expression: Query text containing tags, operators, and parentheses.

    Returns:
        Parsed expression tree.
    """
    parser = _Parser(_tokenize(expression))
    parsed = parser.parse()
    if parser.has_more():
        token = parser.peek()
        raise QueryError(f"Unexpected token: {token.value}")
    return parsed


def _tokenize(expression: str) -> list[_Token]:
    """Tokenize a tag query expression.

    Args:
        expression: Boolean tag expression.

    Returns:
        Token sequence for the parser.
    """
    tokens: list[_Token] = []
    index = 0
    while index < len(expression):
        char = expression[index]
        if char.isspace():
            index += 1
            continue
        if char == "(":
            tokens.append(_Token("LPAREN", char))
            index += 1
            continue
        if char == ")":
            tokens.append(_Token("RPAREN", char))
            index += 1
            continue
        if _is_tag_char(char):
            start = index
            while index < len(expression) and _is_tag_char(expression[index]):
                index += 1
            value = expression[start:index]
            upper = value.upper()
            if upper in {"AND", "OR", "NOT"}:
                tokens.append(_Token(upper, upper))
            else:
                tokens.append(_Token("TAG", value.lower()))
            continue
        raise QueryError(f"Unexpected character in query: {char}")
    if not tokens:
        raise QueryError("Query expression must not be empty")
    return tokens


def _is_tag_char(char: str) -> bool:
    """Return whether a character can appear in a tag token."""
    return char.isalnum() or char in {"_", "-", ".", "/", ":"}


class _Parser:
    """Recursive-descent parser for Boolean tag expressions."""

    def __init__(self, tokens: list[_Token]) -> None:
        """Store tokens for parsing.

        Args:
            tokens: Tokenized query expression.
        """
        self._tokens = tokens
        self._index = 0

    def parse(self) -> _Expression:
        """Parse the full expression."""
        return self._parse_or()

    def has_more(self) -> bool:
        """Return whether unparsed tokens remain."""
        return self._index < len(self._tokens)

    def peek(self) -> _Token:
        """Return the next token without consuming it."""
        return self._tokens[self._index]

    def _parse_or(self) -> _Expression:
        expr = self._parse_and()
        while self._match("OR"):
            expr = _Binary("OR", expr, self._parse_and())
        return expr

    def _parse_and(self) -> _Expression:
        expr = self._parse_not()
        while self._match("AND"):
            expr = _Binary("AND", expr, self._parse_not())
        return expr

    def _parse_not(self) -> _Expression:
        if self._match("NOT"):
            return _Not(self._parse_not())
        return self._parse_primary()

    def _parse_primary(self) -> _Expression:
        if not self.has_more():
            raise QueryError("Unexpected end of query")
        token = self.peek()
        if self._match("TAG"):
            return _Tag(token.value)
        if self._match("LPAREN"):
            expr = self._parse_or()
            if not self._match("RPAREN"):
                raise QueryError("Expected closing parenthesis")
            return expr
        raise QueryError(f"Unexpected token: {token.value}")

    def _match(self, kind: str) -> bool:
        if self.has_more() and self.peek().kind == kind:
            self._index += 1
            return True
        return False
