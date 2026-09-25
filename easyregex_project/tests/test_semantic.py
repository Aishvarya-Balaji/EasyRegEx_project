"""Tests semantic analysis."""

import pytest

from easyregex.errors import SemanticError
from easyregex.lexer import tokenize
from easyregex.parser import parse
from easyregex.semantic import analyze


def analyze_source(source):
    return analyze(parse(tokenize(source)))


def test_symbol_table_records_patterns():
    symbols = analyze_source("pattern a:\n  digit\n\npattern b:\n  letter\n")
    assert len(symbols) == 2
    assert "a" in symbols and "b" in symbols


def test_valid_reference_accepted():
    symbols = analyze_source("pattern a:\n  digit\n\npattern b:\n  use a\n")
    assert symbols.is_declared("a")


def test_forward_reference_accepted():
    # 'b' is used before it is defined; order should not matter
    symbols = analyze_source("pattern a:\n  use b\n\npattern b:\n  digit\n")
    assert len(symbols) == 2


def test_duplicate_pattern_name_rejected():
    with pytest.raises(SemanticError) as info:
        analyze_source("pattern a:\n  digit\n\npattern a:\n  letter\n")
    assert "already defined" in str(info.value)


def test_undefined_reference_rejected():
    with pytest.raises(SemanticError) as info:
        analyze_source("pattern a:\n  use missing\n")
    assert "not defined" in str(info.value)


def test_self_reference_rejected():
    with pytest.raises(SemanticError) as info:
        analyze_source("pattern a:\n  use a\n")
    assert "itself" in str(info.value)


def test_indirect_circular_reference_rejected():
    with pytest.raises(SemanticError) as info:
        analyze_source(
            'pattern a:\n  "x"\n  then use b\n\n'
            'pattern b:\n  "y"\n  then use a\n'
        )
    assert "circular" in str(info.value)


def test_invalid_range_rejected():
    with pytest.raises(SemanticError) as info:
        analyze_source("pattern a:\n  5 to 2 digit\n")
    assert "invalid repetition range" in str(info.value)


def test_zero_repetition_rejected():
    with pytest.raises(SemanticError):
        analyze_source("pattern a:\n  exactly 0 digit\n")


def test_equal_bounds_accepted():
    symbols = analyze_source("pattern a:\n  3 to 3 digit\n")
    assert len(symbols) == 1


def test_test_block_for_undefined_pattern_rejected():
    with pytest.raises(SemanticError) as info:
        analyze_source('pattern a:\n  digit\n\ntest missing:\n  match "1"\n')
    assert "undefined pattern" in str(info.value)


def test_multiple_errors_are_collected():
    with pytest.raises(SemanticError) as info:
        analyze_source(
            "pattern a:\n  use missing\n\n"
            "pattern b:\n  5 to 2 digit\n"
        )
    text = str(info.value)
    assert "2 semantic errors" in text
    assert "not defined" in text
    assert "invalid repetition range" in text


def test_errors_reported_in_source_order():
    with pytest.raises(SemanticError) as info:
        analyze_source(
            "pattern a:\n  9 to 1 digit\n\n"
            "pattern b:\n  use nowhere\n"
        )
    errors = info.value.errors
    assert errors[0].line < errors[1].line
