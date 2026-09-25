"""Tests for Phases 4 and 5: optimization and code generation."""

import re

from easyregex.codegen import generate_all
from easyregex.lexer import tokenize
from easyregex.optimizer import optimize
from easyregex.parser import parse
from easyregex.semantic import analyze


def regexes(source, optimize_ast=True):
    program = parse(tokenize(source))
    symbols = analyze(program)
    if optimize_ast:
        program, _ = optimize(program)
    return generate_all(program, symbols)


def one(source, name="p", optimize_ast=True):
    return regexes(source, optimize_ast)[name]


# -- code generation --------------------------------------------------

def test_literal_is_escaped():
    assert one('pattern p:\n  "a.b"\n') == r"^a\.b$"


def test_character_classes():
    assert one("pattern p:\n  digit\n") == "^[0-9]$"
    assert one("pattern p:\n  letter\n") == "^[a-zA-Z]$"
    assert one("pattern p:\n  letter_or_digit\n") == "^[a-zA-Z0-9]$"
    assert one("pattern p:\n  any\n") == "^.$"


def test_one_or_more_uses_plus():
    assert one("pattern p:\n  one or more digit\n") == "^[0-9]+$"


def test_zero_or_more_uses_star():
    assert one("pattern p:\n  zero or more digit\n") == "^[0-9]*$"


def test_optional_uses_question_mark():
    assert one('pattern p:\n  optional "-"\n') == r"^\-?$"


def test_exactly_uses_brace_count():
    assert one("pattern p:\n  exactly 3 digit\n") == "^[0-9]{3}$"


def test_range_uses_brace_range():
    assert one("pattern p:\n  2 to 15 letter\n") == "^[a-zA-Z]{2,15}$"


def test_alternation_uses_non_capturing_group():
    assert one('pattern p:\n  ("a" or "b")\n') == "^(?:a|b)$"


def test_multichar_literal_is_grouped_before_quantifier():
    # "ab" repeated must be (?:ab)+, not ab+, which would repeat only the b
    assert one('pattern p:\n  one or more "ab"\n') == "^(?:ab)+$"


def test_reference_is_inlined():
    result = regexes('pattern a:\n  digit\n\npattern b:\n  use a\n  then "x"\n')
    assert result["b"] == "^[0-9]x$"


def test_generated_regex_is_anchored():
    regex = one("pattern p:\n  digit\n")
    assert regex.startswith("^") and regex.endswith("$")


def test_generated_regex_compiles():
    for source in [
        'pattern p:\n  one or more letter_or_digit\n  then "@"\n  then ("com" or "org")\n',
        'pattern p:\n  optional ("-" or "+")\n  then one or more digit\n',
        "pattern p:\n  2 to 15 (letter or digit)\n",
    ]:
        re.compile(one(source))


# -- behaviour of the generated regex ---------------------------------

def test_email_regex_behaviour():
    regex = one(
        "pattern p:\n"
        "  one or more letter_or_digit\n"
        '  then "@"\n'
        "  one or more letter\n"
        '  then "."\n'
        '  then ("com" or "org")\n'
    )
    assert re.match(regex, "alice@example.com")
    assert not re.match(regex, "alice@@example.com")
    assert not re.match(regex, "alice@example.net")


def test_anchoring_rejects_partial_match():
    regex = one("pattern p:\n  exactly 3 digit\n")
    assert re.match(regex, "123")
    assert not re.match(regex, "1234")


# -- optimizer --------------------------------------------------------

def test_adjacent_literals_are_folded():
    program = parse(tokenize('pattern p:\n  "a"\n  then "b"\n  then "c"\n'))
    analyze(program)
    optimized, opt = optimize(program)
    assert opt.stats["literals_folded"] == 2
    assert optimized.patterns[0].body.items[0].text == "abc"


def test_single_alternative_group_is_removed():
    program = parse(tokenize('pattern p:\n  ("a")\n'))
    analyze(program)
    _, opt = optimize(program)
    assert opt.stats["groups_removed"] == 1


def test_exactly_one_quantifier_is_removed():
    program = parse(tokenize("pattern p:\n  1 to 1 digit\n"))
    analyze(program)
    _, opt = optimize(program)
    assert opt.stats["quantifiers_removed"] == 1


def test_optimization_preserves_meaning():
    source = 'pattern p:\n  "a"\n  then "b"\n  then one or more digit\n'
    assert one(source, optimize_ast=True) == one(source, optimize_ast=False)


def test_optimizer_reports_no_rewrites_when_minimal():
    program = parse(tokenize("pattern p:\n  one or more digit\n"))
    analyze(program)
    _, opt = optimize(program)
    assert opt.total == 0
