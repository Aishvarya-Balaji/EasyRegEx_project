"""Tests for syntax analysis."""

import pytest

from easyregex.ast_nodes import (
    CharClass, Group, Literal, Quantified, Reference, Sequence,
)
from easyregex.lexer import tokenize
from easyregex.parser import ParserError, parse


def parse_source(source):
    return parse(tokenize(source))


def body_of(source, index=0):
    return parse_source(source).patterns[index].body


def test_simple_pattern_builds_sequence():
    program = parse_source('pattern p:\n  "a"\n')
    assert len(program.patterns) == 1
    assert program.patterns[0].name == "p"
    assert isinstance(program.patterns[0].body, Sequence)


def test_literal_and_charclass_nodes():
    items = body_of('pattern p:\n  "a"\n  then digit\n').items
    assert isinstance(items[0], Literal) and items[0].text == "a"
    assert isinstance(items[1], CharClass) and items[1].name == "digit"


def test_then_keyword_is_optional():
    with_then = body_of('pattern p:\n  "a"\n  then "b"\n').items
    without = body_of('pattern p:\n  "a"\n  "b"\n').items
    assert len(with_then) == len(without) == 2


def test_one_or_more_quantifier():
    node = body_of("pattern p:\n  one or more digit\n").items[0]
    assert isinstance(node, Quantified)
    assert (node.min, node.max) == (1, None)


def test_zero_or_more_quantifier():
    node = body_of("pattern p:\n  zero or more digit\n").items[0]
    assert (node.min, node.max) == (0, None)


def test_optional_quantifier():
    node = body_of('pattern p:\n  optional "-"\n').items[0]
    assert (node.min, node.max) == (0, 1)


def test_exactly_quantifier():
    node = body_of("pattern p:\n  exactly 3 digit\n").items[0]
    assert (node.min, node.max) == (3, 3)


def test_range_quantifier():
    node = body_of("pattern p:\n  2 to 15 letter\n").items[0]
    assert (node.min, node.max) == (2, 15)


def test_alternation_group():
    node = body_of('pattern p:\n  ("com" or "org" or "in")\n').items[0]
    assert isinstance(node, Group)
    assert len(node.alternatives) == 3


def test_group_alternative_can_be_a_sequence():
    node = body_of('pattern p:\n  optional ("." then one or more digit)\n').items[0]
    group = node.inner
    assert isinstance(group, Group)
    assert isinstance(group.alternatives[0], Sequence)


def test_reference_node():
    node = body_of("pattern a:\n  digit\n\npattern b:\n  use a\n", index=1).items[0]
    assert isinstance(node, Reference)
    assert node.name == "a"


def test_multiple_patterns_in_one_file():
    program = parse_source("pattern a:\n  digit\n\npattern b:\n  letter\n")
    assert [p.name for p in program.patterns] == ["a", "b"]


def test_test_block_parsed():
    program = parse_source(
        'pattern p:\n  digit\n\ntest p:\n  match "1"\n  reject "x"\n'
    )
    block = program.tests[0]
    assert block.pattern_name == "p"
    assert [c.should_match for c in block.cases] == [True, False]


def test_missing_colon_raises_syntax_error():
    with pytest.raises(ParserError):
        parse_source("pattern p\n  digit\n")


def test_unclosed_group_raises_syntax_error():
    with pytest.raises(ParserError):
        parse_source('pattern p:\n  ("a" or "b"\n')


def test_empty_pattern_body_raises_syntax_error():
    with pytest.raises(ParserError):
        parse_source("pattern p:\n\npattern q:\n  digit\n")


def test_file_without_patterns_raises_syntax_error():
    with pytest.raises(ParserError):
        parse_source("# only a comment\n")


def test_error_reports_line_number():
    with pytest.raises(ParserError) as info:
        parse_source("pattern p:\n  digit\n\npattern q\n  digit\n")
    assert info.value.line >= 4
