from .ast_nodes import (
    CharClass, Group, Literal, PatternDef, Program, Quantified,
    Reference, Sequence, TestBlock, TestCase,
)
from .errors import ParserError
from .tokens import Token, TokenType

__all__ = ["Parser", "parse", "ParserError"]

# Keywords that can only appear at the start of a top-level construct.
_BLOCK_STARTERS = ("pattern", "test")


class Parser:
    def __init__(self, tokens: list[Token]):
        self.tokens = tokens
        self.pos = 0

    # -- token helpers ------------------------------------------------

    @property
    def current(self) -> Token:
        return self.tokens[self.pos]

    def advance(self) -> Token:
        tok = self.tokens[self.pos]
        if tok.type != TokenType.EOF:
            self.pos += 1
        return tok

    def check(self, type_: TokenType, value: str = None) -> bool:
        tok = self.current
        if tok.type != type_:
            return False
        return value is None or tok.value == value

    def accept(self, type_: TokenType, value: str = None):
        """Consume and return the current token if it matches, else None."""
        if self.check(type_, value):
            return self.advance()
        return None

    def expect(self, type_: TokenType, value: str = None) -> Token:
        """Consume the current token if it matches, otherwise raise."""
        if self.check(type_, value):
            return self.advance()
        expected = value if value is not None else type_.name
        got = self.current
        got_desc = repr(got.value) if got.type != TokenType.EOF else "end of file"
        raise ParserError(
            f"expected {expected}, found {got_desc}", got.line, got.column
        )

    def skip_newlines(self) -> None:
        while self.check(TokenType.NEWLINE):
            self.advance()

    def at_block_start(self) -> bool:
        return (
            self.current.type == TokenType.KEYWORD
            and self.current.value in _BLOCK_STARTERS
        )

    # -- grammar rules ------------------------------------------------

    def parse_program(self) -> Program:
        """program ::= { pattern_def | test_block }"""
        program = Program(line=1, column=1)
        self.skip_newlines()

        while not self.check(TokenType.EOF):
            if self.check(TokenType.KEYWORD, "pattern"):
                program.patterns.append(self.parse_pattern_def())
            elif self.check(TokenType.KEYWORD, "test"):
                program.tests.append(self.parse_test_block())
            else:
                tok = self.current
                raise ParserError(
                    f"expected 'pattern' or 'test' at the start of a block, "
                    f"found {tok.value!r}",
                    tok.line, tok.column,
                )
            self.skip_newlines()

        if not program.patterns:
            raise ParserError("file contains no pattern definitions", 1, 1)

        return program

    def parse_pattern_def(self) -> PatternDef:
        """pattern_def ::= "pattern" IDENT ":" body"""
        kw = self.expect(TokenType.KEYWORD, "pattern")
        name_tok = self.expect(TokenType.IDENT)
        self.expect(TokenType.COLON)

        body = self.parse_body()
        if not body.items:
            raise ParserError(
                f"pattern '{name_tok.value}' has an empty body",
                name_tok.line, name_tok.column,
            )

        return PatternDef(
            line=kw.line, column=kw.column, name=name_tok.value, body=body
        )

    def parse_body(self) -> Sequence:
        """body ::= { [ "then" ] term }"""
        start = self.current
        items = []

        while True:
            self.skip_newlines()
            if self.check(TokenType.EOF) or self.at_block_start():
                break
            # "then" is optional readability sugar between rules
            self.accept(TokenType.KEYWORD, "then")
            self.skip_newlines()
            if self.check(TokenType.EOF) or self.at_block_start():
                break
            items.append(self.parse_term())

        return Sequence(line=start.line, column=start.column, items=items)

    def parse_term(self):
        """term ::= quantified | atom"""
        tok = self.current

        if self.check(TokenType.KEYWORD, "one"):
            self.advance()
            self.expect(TokenType.KEYWORD, "or")
            self.expect(TokenType.KEYWORD, "more")
            inner = self.parse_atom()
            return Quantified(
                line=tok.line, column=tok.column, inner=inner, min=1, max=None
            )

        if self.check(TokenType.KEYWORD, "zero"):
            self.advance()
            self.expect(TokenType.KEYWORD, "or")
            self.expect(TokenType.KEYWORD, "more")
            inner = self.parse_atom()
            return Quantified(
                line=tok.line, column=tok.column, inner=inner, min=0, max=None
            )

        if self.check(TokenType.KEYWORD, "optional"):
            self.advance()
            inner = self.parse_atom()
            return Quantified(
                line=tok.line, column=tok.column, inner=inner, min=0, max=1
            )

        if self.check(TokenType.KEYWORD, "exactly"):
            self.advance()
            count = int(self.expect(TokenType.NUMBER).value)
            inner = self.parse_atom()
            return Quantified(
                line=tok.line, column=tok.column, inner=inner, min=count, max=count
            )

        if self.check(TokenType.NUMBER):
            low = int(self.advance().value)
            self.expect(TokenType.KEYWORD, "to")
            high = int(self.expect(TokenType.NUMBER).value)
            inner = self.parse_atom()
            return Quantified(
                line=tok.line, column=tok.column, inner=inner, min=low, max=high
            )

        return self.parse_atom()

    def parse_atom(self):
        """atom ::= STRING | CLASS | "use" IDENT | "(" term { "or" term } ")" """
        tok = self.current

        if self.check(TokenType.STRING):
            self.advance()
            if tok.value == "":
                raise ParserError("empty string literal", tok.line, tok.column)
            return Literal(line=tok.line, column=tok.column, text=tok.value)

        if self.check(TokenType.CLASS):
            self.advance()
            return CharClass(line=tok.line, column=tok.column, name=tok.value)

        if self.check(TokenType.KEYWORD, "use"):
            self.advance()
            name_tok = self.expect(TokenType.IDENT)
            return Reference(
                line=tok.line, column=tok.column, name=name_tok.value
            )

        if self.check(TokenType.LPAREN):
            self.advance()
            alternatives = []
            self.skip_newlines()
            alternatives.append(self.parse_alternative())
            self.skip_newlines()

            while self.accept(TokenType.KEYWORD, "or"):
                self.skip_newlines()
                alternatives.append(self.parse_alternative())
                self.skip_newlines()

            self.expect(TokenType.RPAREN)
            return Group(
                line=tok.line, column=tok.column, alternatives=alternatives
            )

        got = repr(tok.value) if tok.type != TokenType.EOF else "end of file"
        raise ParserError(
            f"expected a string, a character class, 'use', or '(', found {got}",
            tok.line, tok.column,
        )

    def parse_alternative(self):
        """alternative ::= term { [ "then" ] term }

        One branch of an alternation group. A branch may itself be a
        sequence, so ("." then one or more digit) is a single alternative
        made of two terms rather than a syntax error.
        """
        start = self.current
        items = [self.parse_term()]

        while True:
            self.skip_newlines()
            if (
                self.check(TokenType.RPAREN)
                or self.check(TokenType.EOF)
                or self.check(TokenType.KEYWORD, "or")
                or self.at_block_start()
            ):
                break
            self.accept(TokenType.KEYWORD, "then")
            self.skip_newlines()
            if self.check(TokenType.RPAREN) or self.check(TokenType.EOF):
                break
            items.append(self.parse_term())

        if len(items) == 1:
            return items[0]
        return Sequence(line=start.line, column=start.column, items=items)

    def parse_test_block(self) -> TestBlock:
        """test_block ::= "test" IDENT ":" { test_case }"""
        kw = self.expect(TokenType.KEYWORD, "test")
        name_tok = self.expect(TokenType.IDENT)
        self.expect(TokenType.COLON)

        cases = []
        while True:
            self.skip_newlines()
            if self.check(TokenType.EOF) or self.at_block_start():
                break
            if self.check(TokenType.KEYWORD, "match"):
                verb = self.advance()
                text = self.expect(TokenType.STRING)
                cases.append(TestCase(
                    line=verb.line, column=verb.column,
                    text=text.value, should_match=True,
                ))
            elif self.check(TokenType.KEYWORD, "reject"):
                verb = self.advance()
                text = self.expect(TokenType.STRING)
                cases.append(TestCase(
                    line=verb.line, column=verb.column,
                    text=text.value, should_match=False,
                ))
            else:
                tok = self.current
                raise ParserError(
                    f"expected 'match' or 'reject' inside a test block, "
                    f"found {tok.value!r}",
                    tok.line, tok.column,
                )

        if not cases:
            raise ParserError(
                f"test block for '{name_tok.value}' is empty",
                kw.line, kw.column,
            )

        return TestBlock(
            line=kw.line, column=kw.column,
            pattern_name=name_tok.value, cases=cases,
        )


def parse(tokens: list[Token]) -> Program:
    """Parse a token stream into a Program AST."""
    return Parser(tokens).parse_program()
