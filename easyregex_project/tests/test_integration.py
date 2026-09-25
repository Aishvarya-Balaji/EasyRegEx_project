"""End-to-end tests: the whole pipeline, and the sample input files."""

import pathlib

import pytest

from easyregex.compiler import compile_file, compile_source
from easyregex.errors import LexerError, ParserError, SemanticError

INPUTS = pathlib.Path(__file__).parent.parent / "inputs"


def test_full_pipeline_produces_every_artefact():
    result = compile_source(
        'pattern p:\n  exactly 3 digit\n\ntest p:\n  match "123"\n'
    )
    assert result.tokens
    assert result.ast is not None
    assert result.symbols is not None
    assert result.regexes == {"p": "^[0-9]{3}$"}
    assert result.report.all_passed


def test_declared_tests_are_executed():
    result = compile_source(
        "pattern p:\n  one or more digit\n\n"
        'test p:\n  match "42"\n  reject "x"\n'
    )
    assert result.report.total == 2
    assert result.report.passed == 2


def test_failing_expectation_is_reported():
    # the pattern only accepts digits, so this "match" expectation fails
    result = compile_source(
        'pattern p:\n  one or more digit\n\ntest p:\n  match "abc"\n'
    )
    assert not result.report.all_passed
    assert result.report.failed == 1


def test_compile_without_optimizer_gives_same_regex():
    source = 'pattern p:\n  "a"\n  then "b"\n  then one or more digit\n'
    assert (
        compile_source(source, optimize_ast=True).regexes
        == compile_source(source, optimize_ast=False).regexes
    )


def test_unanchored_mode():
    result = compile_source("pattern p:\n  digit\n", anchored=False)
    assert result.regexes["p"] == "[0-9]"


# -- the sample files shipped with the project ------------------------

@pytest.mark.parametrize("path", sorted(INPUTS.glob("*.rx")), ids=lambda p: p.name)
def test_sample_file_compiles_and_passes_its_own_tests(path):
    result = compile_file(str(path))
    assert result.regexes, f"{path.name} produced no regex"
    assert result.report.all_passed, (
        f"{path.name}: {result.report.summary()}"
    )


# -- the deliberately broken files ------------------------------------

@pytest.mark.parametrize("name,expected", [
    ("lexical_error.rx", LexerError),
    ("syntax_error.rx", ParserError),
    ("undefined_reference.rx", SemanticError),
    ("circular_reference.rx", SemanticError),
    ("bad_range.rx", SemanticError),
    ("duplicate_pattern.rx", SemanticError),
])
def test_error_sample_raises_expected_error(name, expected):
    with pytest.raises(expected):
        compile_file(str(INPUTS / "errors" / name))
