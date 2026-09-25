from dataclasses import dataclass
from enum import Enum, auto


class TokenType(Enum):
    KEYWORD = auto()   # pattern, then, or, use, optional, one, more, zero, ...
    CLASS = auto()     # digit, letter, letter_or_digit, whitespace, any
    STRING = auto()    # "@", "com", "_"
    NUMBER = auto()    # 2, 15, 3
    IDENT = auto()     # user-defined pattern names, e.g. email, username
    COLON = auto()     # :
    LPAREN = auto()    # (
    RPAREN = auto()    # )
    NEWLINE = auto()   # end of a line (rules are separated by newlines)
    EOF = auto()       # end of file marker


# Identifiers are reclassified into KEYWORD / CLASS / IDENT by the lexer
# depending on which of these sets they fall into.

KEYWORDS = {
    # pattern definitions
    "pattern", "then", "or", "use", "optional",
    "one", "more", "zero", "exactly", "to",
    # test blocks
    "test", "match", "reject",
}

CLASSES = {
    "digit", "letter", "letter_or_digit", "whitespace", "any",
}


@dataclass
class Token:
    type: TokenType
    value: str
    line: int
    column: int

    def __repr__(self):
        return f"Token({self.type.name}, {self.value!r}, line={self.line}, col={self.column})"
