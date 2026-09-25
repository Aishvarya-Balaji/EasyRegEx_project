from dataclasses import dataclass, field


@dataclass
class Node:
    """Base class. Every node records where it came from in the source."""

    line: int = field(default=0, compare=False)
    column: int = field(default=0, compare=False)

    def describe(self) -> str:
        return self.__class__.__name__


@dataclass
class Literal(Node):
    """Text matched exactly, e.g. "@" or "com"."""

    text: str = ""

    def describe(self) -> str:
        return f'Literal("{self.text}")'


@dataclass
class CharClass(Node):
    """A built-in character class: digit, letter, letter_or_digit, ..."""

    name: str = ""

    def describe(self) -> str:
        return f"CharClass({self.name})"


@dataclass
class Reference(Node):
    """A reference to another named pattern, written `use <name>`."""

    name: str = ""

    def describe(self) -> str:
        return f"Reference(use {self.name})"


@dataclass
class Group(Node):
    """An alternation group: (A or B or C). Matches any one alternative."""

    alternatives: list = field(default_factory=list)

    def describe(self) -> str:
        return f"Group({len(self.alternatives)} alternatives)"


@dataclass
class Quantified(Node):
    """A repeated element. `max` is None for an open-ended upper bound.

    one or more X  -> min=1, max=None
    zero or more X -> min=0, max=None
    optional X     -> min=0, max=1
    exactly N X    -> min=N, max=N
    N to M X       -> min=N, max=M
    """

    inner: Node = None
    min: int = 1
    max: int = None

    def describe(self) -> str:
        upper = "inf" if self.max is None else self.max
        return f"Quantified(min={self.min}, max={upper})"


@dataclass
class Sequence(Node):
    """An ordered series of elements that must match one after another."""

    items: list = field(default_factory=list)

    def describe(self) -> str:
        return f"Sequence({len(self.items)} items)"


@dataclass
class PatternDef(Node):
    """A named pattern definition: `pattern <name>: <body>`."""

    name: str = ""
    body: Sequence = None

    def describe(self) -> str:
        return f"PatternDef({self.name})"


@dataclass
class TestCase(Node):
    """A single expectation inside a test block."""

    text: str = ""
    should_match: bool = True

    def describe(self) -> str:
        verb = "match" if self.should_match else "reject"
        return f'TestCase({verb} "{self.text}")'


@dataclass
class TestBlock(Node):
    """A block of expectations for one pattern: `test <name>: ...`."""

    pattern_name: str = ""
    cases: list = field(default_factory=list)

    def describe(self) -> str:
        return f"TestBlock({self.pattern_name}, {len(self.cases)} cases)"


@dataclass
class Program(Node):
    """The root node: everything defined in one .rx file."""

    patterns: list = field(default_factory=list)
    tests: list = field(default_factory=list)

    def describe(self) -> str:
        return f"Program({len(self.patterns)} patterns, {len(self.tests)} test blocks)"


# ---------------------------------------------------------------------------
# Tree printing
# ---------------------------------------------------------------------------

def _children(node: Node) -> list:
    """Return the child nodes of any AST node, for traversal and printing."""
    if isinstance(node, Program):
        return list(node.patterns) + list(node.tests)
    if isinstance(node, PatternDef):
        return [node.body] if node.body is not None else []
    if isinstance(node, Sequence):
        return list(node.items)
    if isinstance(node, Group):
        return list(node.alternatives)
    if isinstance(node, Quantified):
        return [node.inner] if node.inner is not None else []
    if isinstance(node, TestBlock):
        return list(node.cases)
    return []


def dump(node: Node, prefix: str = "", is_root: bool = True,
         is_last: bool = True) -> str:
    """Render an AST as an indented tree, for the --ast command-line flag."""
    if is_root:
        lines = [node.describe()]
        child_prefix = ""
    else:
        connector = "`-- " if is_last else "|-- "
        lines = [prefix + connector + node.describe()]
        child_prefix = prefix + ("    " if is_last else "|   ")

    kids = _children(node)
    for i, child in enumerate(kids):
        lines.append(
            dump(child, child_prefix, is_root=False, is_last=(i == len(kids) - 1))
        )
    return "\n".join(lines)
