"""Tests for lexical analysis."""

import pytest

from easyregex.lexer import LexerError, tokenize
from easyregex.tokens import TokenType


def kinds(source):
    return [t.type for t in tokenize(source) if t.type != TokenType.EOF]


def test_pattern_header_tokens():
    tokens = tokenize("pattern email:\n")
    assert tokens[0].type == TokenType.KEYWORD and tokens[0].value == "pattern"
    assert tokens[1].type == TokenType.IDENT and tokens[1].value == "email"
    assert tokens[2].type == TokenType.COLON


def test_string_literal_strips_quotes():
    tokens = tokenize('"@"')
    assert tokens[0].type == TokenType.STRING
    assert tokens[0].value == "@"


def test_number_literal():
    tokens = tokenize("15")
    assert tokens[0].type == TokenType.NUMBER
    assert tokens[0].value == "15"


def test_multi_word_keyword_sequence():
    tokens = tokenize("one or more")
    assert [(t.type, t.value) for t in tokens if t.type != TokenType.EOF] == [
        (TokenType.KEYWORD, "one"),
        (TokenType.KEYWORD, "or"),
        (TokenType.KEYWORD, "more"),
    ]


def test_builtin_classes_recognized():
    assert kinds("digit letter whitespace letter_or_digit any") == [TokenType.CLASS] * 5


def test_test_block_keywords_recognized():
    assert kinds("test match reject") == [TokenType.KEYWORD] * 3


def test_comment_produces_no_token():
    tokens = tokenize("# a comment\npattern x:")
    assert tokens[0].type == TokenType.NEWLINE
    assert tokens[1].type == TokenType.KEYWORD


def test_alternation_group_tokens():
    assert kinds('("com" or "org")') == [
        TokenType.LPAREN, TokenType.STRING, TokenType.KEYWORD,
        TokenType.STRING, TokenType.RPAREN,
    ]


def test_full_username_pattern_tokenizes_cleanly():
    tokens = tokenize(
        'pattern username:\n'
        '  letter\n'
        '  then 2 to 15 (letter or digit or "_")\n'
    )
    assert tokens[-1].type == TokenType.EOF
    assert any(t.value == "username" for t in tokens)
    assert any(t.type == TokenType.NUMBER and t.value == "15" for t in tokens)


def test_line_and_column_tracked():
    tokens = tokenize("pattern x:\n  letter\n")
    letter = next(t for t in tokens if t.value == "letter")
    assert letter.line == 2
    assert letter.column == 3


def test_unexpected_character_raises_lexer_error():
    with pytest.raises(LexerError) as info:
        tokenize("pattern x: $")
    assert info.value.line == 1


def test_unterminated_string_raises_lexer_error():
    with pytest.raises(LexerError):
        tokenize('pattern x:\n  "unterminated')


def test_identifier_not_a_keyword_or_class():
    tokens = tokenize("my_pattern_name")
    assert tokens[0].type == TokenType.IDENT
    assert tokens[0].value == "my_pattern_name"


def test_token_stream_always_ends_with_eof():
    assert tokenize("").pop().type == TokenType.EOF
    assert tokenize("pattern x:\n  digit").pop().type == TokenType.EOF
