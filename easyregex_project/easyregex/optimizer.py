from dataclasses import replace

from .ast_nodes import (
    CharClass, Group, Literal, PatternDef, Program, Quantified,
    Reference, Sequence,
)

__all__ = ["Optimizer", "optimize"]


class Optimizer:
    def __init__(self):
        self.stats = {
            "literals_folded": 0,
            "sequences_flattened": 0,
            "groups_removed": 0,
            "quantifiers_removed": 0,
        }

    @property
    def total(self) -> int:
        return sum(self.stats.values())

    def optimize_program(self, program: Program) -> Program:
        patterns = [
            replace(p, body=self._wrap_sequence(self.visit(p.body)))
            for p in program.patterns
        ]
        return replace(program, patterns=patterns)

    # -- traversal ----------------------------------------------------

    def visit(self, node):
        if isinstance(node, Sequence):
            return self.visit_sequence(node)
        if isinstance(node, Group):
            return self.visit_group(node)
        if isinstance(node, Quantified):
            return self.visit_quantified(node)
        # Literal, CharClass and Reference are already minimal.
        return node

    def visit_sequence(self, node: Sequence):
        items = []
        for item in node.items:
            optimized = self.visit(item)

            # 2. flatten a nested sequence into this one
            if isinstance(optimized, Sequence):
                self.stats["sequences_flattened"] += 1
                items.extend(optimized.items)
                continue

            items.append(optimized)

        items = self._fold_literals(items)

        # 5. a sequence of one element is just that element
        if len(items) == 1:
            return items[0]

        return replace(node, items=items)

    def visit_group(self, node: Group):
        alternatives = [self.visit(alt) for alt in node.alternatives]

        # 3. a group with a single alternative offers no choice
        if len(alternatives) == 1:
            self.stats["groups_removed"] += 1
            return alternatives[0]

        return replace(node, alternatives=alternatives)

    def visit_quantified(self, node: Quantified):
        inner = self.visit(node.inner)

        # 4. "exactly 1 X" is just X
        if node.min == 1 and node.max == 1:
            self.stats["quantifiers_removed"] += 1
            return inner

        return replace(node, inner=inner)

    # -- helpers ------------------------------------------------------

    def _fold_literals(self, items: list) -> list:
        """1. Merge runs of adjacent Literal nodes into a single Literal."""
        folded = []
        for item in items:
            if (
                folded
                and isinstance(item, Literal)
                and isinstance(folded[-1], Literal)
            ):
                previous = folded[-1]
                folded[-1] = replace(previous, text=previous.text + item.text)
                self.stats["literals_folded"] += 1
            else:
                folded.append(item)
        return folded

    @staticmethod
    def _wrap_sequence(node):
        """A pattern body must always be a Sequence, even after unwrapping."""
        if isinstance(node, Sequence):
            return node
        return Sequence(line=node.line, column=node.column, items=[node])

    def report(self) -> str:
        if self.total == 0:
            return "Optimizer: no rewrites applied (AST already minimal)."
        parts = [
            f"{name.replace('_', ' ')}: {count}"
            for name, count in self.stats.items() if count
        ]
        return f"Optimizer: {self.total} rewrites applied (" + ", ".join(parts) + ")."


def optimize(program: Program):
    """Return (optimized_program, optimizer) so stats can be reported."""
    opt = Optimizer()
    return opt.optimize_program(program), opt
