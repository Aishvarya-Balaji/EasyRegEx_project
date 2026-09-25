from .ast_nodes import (
    CharClass, Group, Literal, PatternDef, Program, Quantified,
    Reference, Sequence,
)
from .errors import SemanticError

__all__ = ["SymbolTable", "SemanticAnalyzer", "analyze", "SemanticError"]


class SymbolTable:
    """Maps pattern names to their definitions.

    This is the compiler's record of every name the program declares. The
    code generator consults it to resolve `use X` references.
    """

    def __init__(self):
        self._symbols: dict[str, PatternDef] = {}

    def declare(self, pattern: PatternDef) -> None:
        self._symbols[pattern.name] = pattern

    def is_declared(self, name: str) -> bool:
        return name in self._symbols

    def lookup(self, name: str) -> PatternDef:
        return self._symbols[name]

    def names(self) -> list[str]:
        return list(self._symbols)

    def __len__(self) -> int:
        return len(self._symbols)

    def __contains__(self, name: str) -> bool:
        return name in self._symbols


class SemanticAnalyzer:
    def __init__(self, program: Program):
        self.program = program
        self.symbols = SymbolTable()
        self.errors: list[SemanticError] = []

    # -- entry point --------------------------------------------------

    def analyze(self) -> SymbolTable:
        self._build_symbol_table()
        self._check_references_and_ranges()
        self._check_cycles()
        self._check_test_blocks()

        if self.errors:
            # Report in source order so the list reads top to bottom.
            self.errors.sort(key=lambda e: (e.line, e.column))
            raise self.errors[0] if len(self.errors) == 1 else SemanticErrorGroup(self.errors)

        return self.symbols

    # -- pass 1: declarations -----------------------------------------

    def _build_symbol_table(self) -> None:
        seen: dict[str, PatternDef] = {}
        for pattern in self.program.patterns:
            if pattern.name in seen:
                first = seen[pattern.name]
                self.errors.append(SemanticError(
                    f"pattern '{pattern.name}' is already defined at line {first.line}",
                    pattern.line, pattern.column,
                ))
                continue
            seen[pattern.name] = pattern
            self.symbols.declare(pattern)

    # -- pass 2: references and quantifier ranges ----------------------

    def _check_references_and_ranges(self) -> None:
        for pattern in self.program.patterns:
            self._walk(pattern.body, pattern.name)

    def _walk(self, node, owner: str) -> None:
        if isinstance(node, Reference):
            if node.name == owner:
                self.errors.append(SemanticError(
                    f"pattern '{owner}' refers to itself",
                    node.line, node.column,
                ))
            elif not self.symbols.is_declared(node.name):
                self.errors.append(SemanticError(
                    f"pattern '{node.name}' is not defined",
                    node.line, node.column,
                ))
            return

        if isinstance(node, Quantified):
            self._check_range(node)
            self._walk(node.inner, owner)
            return

        if isinstance(node, Sequence):
            for item in node.items:
                self._walk(item, owner)
            return

        if isinstance(node, Group):
            if not node.alternatives:
                self.errors.append(SemanticError(
                    "alternation group is empty", node.line, node.column
                ))
            for alt in node.alternatives:
                self._walk(alt, owner)
            return

        # Literal and CharClass are always valid on their own.
        if isinstance(node, (Literal, CharClass)):
            return

    def _check_range(self, node: Quantified) -> None:
        if node.min < 0:
            self.errors.append(SemanticError(
                "repetition count cannot be negative", node.line, node.column
            ))
            return

        if node.max is not None:
            if node.max < node.min:
                self.errors.append(SemanticError(
                    f"invalid repetition range: {node.min} to {node.max} "
                    f"(the upper bound is smaller than the lower bound)",
                    node.line, node.column,
                ))
            elif node.max == 0:
                self.errors.append(SemanticError(
                    "repetition count of 0 matches nothing; remove the element instead",
                    node.line, node.column,
                ))

    # -- pass 3: circular references ----------------------------------

    def _check_cycles(self) -> None:
        """Depth-first search over the reference graph, reporting cycles."""
        WHITE, GREY, BLACK = 0, 1, 2
        colour = {name: WHITE for name in self.symbols.names()}
        reported: set[tuple] = set()

        def refs_of(name: str):
            found = []

            def collect(node):
                if isinstance(node, Reference):
                    found.append(node)
                elif isinstance(node, Quantified):
                    collect(node.inner)
                elif isinstance(node, Sequence):
                    for item in node.items:
                        collect(item)
                elif isinstance(node, Group):
                    for alt in node.alternatives:
                        collect(alt)

            collect(self.symbols.lookup(name).body)
            return found

        def visit(name: str, stack: list[str]) -> None:
            colour[name] = GREY
            stack.append(name)

            for ref in refs_of(name):
                target = ref.name
                if target not in colour:
                    continue  # undefined; already reported in pass 2
                if colour[target] == GREY:
                    cycle = stack[stack.index(target):] + [target]
                    key = tuple(sorted(set(cycle)))
                    if key not in reported:
                        reported.add(key)
                        self.errors.append(SemanticError(
                            "circular reference: " + " -> ".join(cycle),
                            ref.line, ref.column,
                        ))
                elif colour[target] == WHITE:
                    visit(target, stack)

            stack.pop()
            colour[name] = BLACK

        for name in self.symbols.names():
            if colour[name] == WHITE:
                visit(name, [])

    # -- pass 4: test blocks ------------------------------------------

    def _check_test_blocks(self) -> None:
        for block in self.program.tests:
            if not self.symbols.is_declared(block.pattern_name):
                self.errors.append(SemanticError(
                    f"test block refers to undefined pattern '{block.pattern_name}'",
                    block.line, block.column,
                ))


class SemanticErrorGroup(SemanticError):
    """Several semantic errors reported together."""

    def __init__(self, errors: list[SemanticError]):
        self.errors = errors
        first = errors[0]
        self.message = first.message
        self.line = first.line
        self.column = first.column
        Exception.__init__(self, self.format())

    def format(self) -> str:
        head = f"{len(self.errors)} semantic errors found:"
        body = "\n".join("  " + e.format() for e in self.errors)
        return head + "\n" + body


def analyze(program: Program) -> SymbolTable:
    """Validate a program and return its symbol table."""
    return SemanticAnalyzer(program).analyze()
