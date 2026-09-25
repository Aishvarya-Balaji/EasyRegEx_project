from dataclasses import dataclass, field

from .ast_nodes import Program, dump
from .codegen import CodeGenerator
from .errors import CompilerError
from .lexer import tokenize
from .optimizer import Optimizer, optimize
from .parser import parse
from .semantic import SymbolTable, analyze
from .testrunner import TestReport, run_tests

__all__ = ["CompilationResult", "compile_source", "compile_file"]


@dataclass
class CompilationResult:
    """Everything the compiler produced for one source file."""

    source: str
    tokens: list = field(default_factory=list)
    ast: Program = None
    optimized_ast: Program = None
    symbols: SymbolTable = None
    optimizer: Optimizer = None
    regexes: dict = field(default_factory=dict)
    report: TestReport = None

    def ast_dump(self, optimized: bool = False) -> str:
        tree = self.optimized_ast if optimized else self.ast
        return dump(tree) if tree is not None else "(no AST)"


def compile_source(source: str, optimize_ast: bool = True,
                   anchored: bool = True) -> CompilationResult:
    """Run the full pipeline on EasyRegEx source text.

    Raises a CompilerError subclass (LexerError, ParserError or
    SemanticError) if any phase rejects the program.
    """
    result = CompilationResult(source=source)

    # Phase 1: lexical analysis
    result.tokens = tokenize(source)

    # Phase 2: syntax analysis
    result.ast = parse(result.tokens)

    # Phase 3: semantic analysis
    result.symbols = analyze(result.ast)

    # Phase 4: optimization
    if optimize_ast:
        result.optimized_ast, result.optimizer = optimize(result.ast)
    else:
        result.optimized_ast = result.ast
        result.optimizer = Optimizer()

    # Phase 5: code generation
    generator = CodeGenerator(result.symbols, anchored=anchored)
    result.regexes = generator.generate_all(result.optimized_ast)

    # Phase 6: test execution
    result.report = run_tests(result.optimized_ast, result.regexes)

    return result


def compile_file(path: str, **kwargs) -> CompilationResult:
    """Read a .rx file from disk and compile it."""
    with open(path, "r", encoding="utf-8") as f:
        return compile_source(f.read(), **kwargs)
