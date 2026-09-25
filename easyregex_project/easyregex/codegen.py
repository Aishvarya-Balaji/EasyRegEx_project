import re

from .ast_nodes import (
    CharClass, Group, Literal, PatternDef, Program, Quantified,
    Reference, Sequence,
)
from .semantic import SymbolTable

__all__ = ["CodeGenerator", "generate", "generate_all", "CLASS_PATTERNS"]


# Built-in character classes and the regex each one compiles to.
CLASS_PATTERNS = {
    "digit": "[0-9]",
    "letter": "[a-zA-Z]",
    "letter_or_digit": "[a-zA-Z0-9]",
    "whitespace": r"\s",
    "any": ".",
}


class CodeGenerator:
    def __init__(self, symbols: SymbolTable, anchored: bool = True):
        self.symbols = symbols
        self.anchored = anchored
        self._cache: dict[str, str] = {}

    # -- entry points -------------------------------------------------

    def generate(self, pattern: PatternDef) -> str:
        """Generate the complete regular expression for one pattern."""
        body, _ = self.emit(pattern.body)
        return f"^{body}$" if self.anchored else body

    def generate_all(self, program: Program) -> dict[str, str]:
        """Generate the regex for every pattern, in declaration order."""
        return {p.name: self.generate(p) for p in program.patterns}

    # -- translation rules --------------------------------------------

    def emit(self, node) -> tuple[str, bool]:
        """Return (regex_fragment, is_atomic) for an AST node."""
        if isinstance(node, Literal):
            return self.emit_literal(node)
        if isinstance(node, CharClass):
            return self.emit_charclass(node)
        if isinstance(node, Group):
            return self.emit_group(node)
        if isinstance(node, Quantified):
            return self.emit_quantified(node)
        if isinstance(node, Sequence):
            return self.emit_sequence(node)
        if isinstance(node, Reference):
            return self.emit_reference(node)
        raise TypeError(f"no translation rule for {type(node).__name__}")

    def emit_literal(self, node: Literal) -> tuple[str, bool]:
        # re.escape neutralises characters that would otherwise be
        # interpreted as regex syntax, e.g. "." becomes "\.".
        text = re.escape(node.text)
        return text, len(node.text) == 1

    def emit_charclass(self, node: CharClass) -> tuple[str, bool]:
        return CLASS_PATTERNS[node.name], True

    def emit_group(self, node: Group) -> tuple[str, bool]:
        alternatives = [self.emit(alt)[0] for alt in node.alternatives]
        return "(?:" + "|".join(alternatives) + ")", True

    def emit_sequence(self, node: Sequence) -> tuple[str, bool]:
        fragments = [self.emit(item) for item in node.items]
        text = "".join(fragment for fragment, _ in fragments)
        atomic = len(fragments) == 1 and fragments[0][1]
        return text, atomic

    def emit_quantified(self, node: Quantified) -> tuple[str, bool]:
        inner, atomic = self.emit(node.inner)
        # A quantifier applies to one element only, so anything that is
        # not already a single unit has to be grouped first.
        if not atomic:
            inner = f"(?:{inner})"
        return inner + self._suffix(node), True

    def emit_reference(self, node: Reference) -> tuple[str, bool]:
        """Inline the referenced pattern's regex.

        Semantic analysis has already proved the reference graph is
        acyclic, so this recursion always terminates. Results are cached
        because the same pattern may be referenced many times.

        A fragment that is already a single unit, such as (?:a|b), is
        inlined as-is; only a multi-part fragment needs wrapping, so that
        the inlined pattern still behaves as one element in its new
        context.
        """
        if node.name not in self._cache:
            target = self.symbols.lookup(node.name)
            self._cache[node.name] = self.emit(target.body)

        text, atomic = self._cache[node.name]
        if atomic:
            return text, True
        return f"(?:{text})", True

    @staticmethod
    def _suffix(node: Quantified) -> str:
        low, high = node.min, node.max
        if low == 1 and high is None:
            return "+"
        if low == 0 and high is None:
            return "*"
        if low == 0 and high == 1:
            return "?"
        if high is None:
            return "{%d,}" % low
        if low == high:
            return "{%d}" % low
        return "{%d,%d}" % (low, high)


def generate(pattern: PatternDef, symbols: SymbolTable, anchored: bool = True) -> str:
    return CodeGenerator(symbols, anchored).generate(pattern)


def generate_all(program: Program, symbols: SymbolTable, anchored: bool = True) -> dict:
    return CodeGenerator(symbols, anchored).generate_all(program)
