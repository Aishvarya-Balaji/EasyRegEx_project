import re

from .errors import LexerError
from .tokens import CLASSES, KEYWORDS, Token, TokenType

__all__ = ["tokenize", "LexerError"]


# Order matters: patterns are tried top to bottom, so more specific
# patterns (comments, strings) must come before the catch-all IDENT
# pattern, and MISMATCH must always be last.
_TOKEN_SPEC = [
    ("COMMENT",      r"#[^\n]*"),
    ("UNTERMINATED", r'"[^"\n]*$'),
    ("STRING",       r'"[^"\n]*"'),
    ("NUMBER",       r"\d+"),
    ("IDENT",        r"[a-zA-Z_][a-zA-Z0-9_]*"),
    ("COLON",        r":"),
    ("LPAREN",       r"\("),
    ("RPAREN",       r"\)"),
    ("NEWLINE",      r"\n"),
    ("SKIP",         r"[ \t\r]+"),
    ("MISMATCH",     r"."),
]

_MASTER_PATTERN = re.compile(
    "|".join(f"(?P<{name}>{pattern})" for name, pattern in _TOKEN_SPEC),
    re.MULTILINE,
)


def tokenize(source: str) -> list[Token]:
    """Convert EasyRegEx source text into a list of Token objects.

    The returned list always ends with a single EOF token. Raises
    LexerError on unrecognized characters or an unterminated string
    literal (a quote with no closing quote before end of line).
    """
    tokens: list[Token] = []
    line = 1
    line_start = 0

    for match in _MASTER_PATTERN.finditer(source):
        kind = match.lastgroup
        value = match.group()
        column = match.start() - line_start + 1

        if kind == "NEWLINE":
            tokens.append(Token(TokenType.NEWLINE, value, line, column))
            line += 1
            line_start = match.end()
            continue

        if kind in ("SKIP", "COMMENT"):
            continue

        if kind == "UNTERMINATED":
            raise LexerError("unterminated string literal", line, column)

        if kind == "MISMATCH":
            raise LexerError(f"unexpected character {value!r}", line, column)

        if kind == "STRING":
            # Strip the surrounding quotes so later phases work with the
            # literal's actual contents, e.g. '"@"' -> '@'.
            tokens.append(Token(TokenType.STRING, value[1:-1], line, column))
            continue

        if kind == "NUMBER":
            tokens.append(Token(TokenType.NUMBER, value, line, column))
            continue

        if kind == "IDENT":
            if value in KEYWORDS:
                tokens.append(Token(TokenType.KEYWORD, value, line, column))
            elif value in CLASSES:
                tokens.append(Token(TokenType.CLASS, value, line, column))
            else:
                tokens.append(Token(TokenType.IDENT, value, line, column))
            continue

        if kind == "COLON":
            tokens.append(Token(TokenType.COLON, value, line, column))
        elif kind == "LPAREN":
            tokens.append(Token(TokenType.LPAREN, value, line, column))
        elif kind == "RPAREN":
            tokens.append(Token(TokenType.RPAREN, value, line, column))

    tokens.append(Token(TokenType.EOF, "", line, 1))
    return tokens
