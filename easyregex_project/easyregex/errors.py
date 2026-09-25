class CompilerError(Exception):
    """Base class for every error raised by the compiler."""

    phase = "Compiler"

    def __init__(self, message: str, line: int, column: int):
        self.message = message
        self.line = line
        self.column = column
        super().__init__(self.format())

    def format(self) -> str:
        return f"{self.phase} error at line {self.line}, column {self.column}: {self.message}"


class LexerError(CompilerError):
    """Raised when the source contains text that does not form a valid token."""

    phase = "Lexer"


class ParserError(CompilerError):
    """Raised when the token stream does not match the EasyRegEx grammar."""

    phase = "Syntax"


class SemanticError(CompilerError):
    """Raised when a program is grammatically valid but meaningless.

    Examples: referring to a pattern that was never defined, defining the
    same pattern name twice, or writing a quantifier range like `5 to 2`.
    """

    phase = "Semantic"
