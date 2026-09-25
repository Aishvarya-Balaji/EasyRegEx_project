import sys

from easyregex.compiler import compile_file
from easyregex.errors import CompilerError
from easyregex.testrunner import match_string

USAGE = __doc__


def print_heading(text: str) -> None:
    print()
    print(text)
    print("=" * len(text))


def print_tokens(tokens) -> None:
    """Print the token stream as an aligned table."""
    def fmt(value: str) -> str:
        value = value.replace("\n", "\\n").replace("\t", "\\t")
        return value if len(value) <= 20 else value[:17] + "..."

    rows = [
        (t.type.name, fmt(t.value), str(t.line), str(t.column)) for t in tokens
    ]
    headers = ("TOKEN TYPE", "LEXEME", "LINE", "COL")
    widths = [max(len(headers[i]), *(len(r[i]) for r in rows)) for i in range(4)]

    def row(cells):
        print("  ".join(c.ljust(widths[i]) for i, c in enumerate(cells)))

    row(headers)
    row(["-" * w for w in widths])
    for r in rows:
        row(r)
    print(f"\n{len(tokens)} tokens produced.")


def print_symbols(symbols) -> None:
    names = symbols.names()
    if not names:
        print("(empty)")
        return
    for name in names:
        pattern = symbols.lookup(name)
        print(f"  {name:<20} defined at line {pattern.line}")
    print(f"\n{len(names)} pattern(s) declared.")


def print_regexes(regexes: dict) -> None:
    if not regexes:
        print("(none)")
        return
    width = max(len(name) for name in regexes)
    for name, regex in regexes.items():
        print(f"  {name.ljust(width)}  ->  {regex}")


def print_report(report) -> None:
    for result in report.results:
        print("  " + result.describe())
    print()
    print(report.summary())


def main(argv: list[str]) -> int:
    args = [a for a in argv[1:]]
    if not args or args[0] in ("-h", "--help"):
        print(USAGE)
        return 0 if args else 1

    path = args[0]
    flags = set(args[1:])

    match_target = None
    if "--match" in flags:
        index = args.index("--match")
        if index + 1 >= len(args):
            print("Error: --match requires a string argument")
            return 1
        match_target = args[index + 1]
        flags.discard(match_target)
    flags.discard("--match")

    show_all = "--all" in flags
    show_tokens = show_all or "--tokens" in flags
    show_ast = show_all or "--ast" in flags
    show_symbols = show_all or "--symbols" in flags
    show_regex = show_all or "--regex" in flags or not (
        show_tokens or show_ast or show_symbols or "--test" in flags
    )
    run_test_cases = show_all or "--test" in flags or not (
        "--tokens" in flags or "--ast" in flags or "--symbols" in flags
        or "--regex" in flags
    )
    optimize_ast = "--no-optimize" not in flags

    print(f"Compiling {path} ...")

    try:
        result = compile_file(path, optimize_ast=optimize_ast)
    except FileNotFoundError:
        print(f"Error: file not found: {path}")
        return 1
    except CompilerError as e:
        print()
        print(e.format())
        return 1

    if show_tokens:
        print_heading("Phase 1 - Lexical Analysis: token stream")
        print_tokens(result.tokens)

    if show_ast:
        print_heading("Phase 2 - Syntax Analysis: abstract syntax tree")
        print(result.ast_dump())

    if show_symbols:
        print_heading("Phase 3 - Semantic Analysis: symbol table")
        print_symbols(result.symbols)

    if show_all and optimize_ast:
        print_heading("Phase 4 - Optimization")
        print(result.optimizer.report())
        print()
        print(result.ast_dump(optimized=True))

    if show_regex:
        print_heading("Phase 5 - Code Generation: regular expressions")
        print_regexes(result.regexes)
        if optimize_ast and result.optimizer.total:
            print()
            print(result.optimizer.report())

    if run_test_cases and result.report.total:
        print_heading("Phase 6 - Test Execution")
        print_report(result.report)

    if match_target is not None:
        print_heading(f"Matching {match_target!r}")
        for name, regex in result.regexes.items():
            verdict = "MATCH" if match_string(regex, match_target) else "NO MATCH"
            print(f"  {name:<20} {verdict}")

    if result.report is not None and not result.report.all_passed:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
