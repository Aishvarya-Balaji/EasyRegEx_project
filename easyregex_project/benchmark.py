"""Performance evaluation for the EasyRegEx compiler.

Run from the project folder:

    python benchmark.py

Four measurements are printed:

  1. Per-sample metrics: tokens, AST size, regex length, compile time.
  2. The effect of the optimizer on inputs designed to trigger each rewrite.
  3. Scalability with named references: N patterns, each using the previous.
  4. Scalability with independent patterns: N patterns, no references.

Times are the mean of repeated runs, in milliseconds. Memory is the peak
allocation measured with tracemalloc during one compilation. Absolute
numbers depend on the machine; the growth trend is what matters.
"""

import glob
import os
import platform
import statistics
import time
import tracemalloc

from easyregex.ast_nodes import _children
from easyregex.compiler import compile_file, compile_source

HERE = os.path.dirname(os.path.abspath(__file__))


def count_nodes(node) -> int:
    return 1 + sum(count_nodes(child) for child in _children(node))


def mean_ms(source: str, repeats: int) -> float:
    samples = []
    for _ in range(repeats):
        start = time.perf_counter()
        compile_source(source)
        samples.append((time.perf_counter() - start) * 1000)
    return statistics.mean(samples)


def peak_kb(source: str) -> float:
    tracemalloc.start()
    compile_source(source)
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return peak / 1024


def heading(text: str) -> None:
    print()
    print(text)
    print("=" * len(text))


def sample_metrics() -> None:
    heading("1. Per-sample metrics (mean of 300 runs)")
    columns = ("file", "tokens", "AST nodes", "patterns", "cases", "passed", "rewrites",
               "regex len", "ms")
    print(f"{columns[0]:<15}{columns[1]:>8}{columns[2]:>11}{columns[3]:>10}{columns[4]:>7}"
          f"{columns[5]:>8}{columns[6]:>10}{columns[7]:>11}{columns[8]:>9}")
    for path in sorted(glob.glob(os.path.join(HERE, "inputs", "*.rx"))):
        result = compile_file(path)
        plain = compile_file(path, optimize_ast=False)
        with open(path, encoding="utf-8") as f:
            source = f.read()
        nodes = f"{count_nodes(plain.ast)}->{count_nodes(result.optimized_ast)}"
        length = (f"{sum(len(r) for r in plain.regexes.values())}->"
                  f"{sum(len(r) for r in result.regexes.values())}")
        print(f"{os.path.basename(path):<15}{len(result.tokens):>8}{nodes:>11}"
              f"{len(result.regexes):>10}{result.report.total:>7}{result.report.passed:>8}"
              f"{result.optimizer.total:>10}{length:>11}{mean_ms(source, 300):>9.3f}")


def optimizer_effect() -> None:
    heading("2. Optimizer effect on designed inputs")
    demos = {
        "literal run": 'pattern p:\n  "a"\n  then "b"\n  then "c"\n  then "d"\n  then one or more digit\n',
        "single group": 'pattern p:\n  ("x")\n  then one or more digit\n',
        "exactly one": 'pattern p:\n  1 to 1 letter\n  then 1 to 1 digit\n',
        "mixed": 'pattern p:\n  "ab"\n  then "cd"\n  then ("-")\n  then 1 to 1 digit\n  then "ef"\n',
    }
    print(f"{'input':<14}{'rewrites':>9}{'AST nodes':>12}{'regex length':>15}")
    for name, source in demos.items():
        plain = compile_source(source, optimize_ast=False)
        result = compile_source(source)
        nodes = f"{count_nodes(plain.ast)}->{count_nodes(result.optimized_ast)}"
        length = f"{len(plain.regexes['p'])}->{len(result.regexes['p'])}"
        print(f"{name:<14}{result.optimizer.total:>9}{nodes:>12}{length:>15}")


def chained_program(n: int) -> str:
    parts = ["pattern p0:\n  one or more digit\n"]
    for i in range(1, n):
        parts.append(
            f'pattern p{i}:\n  use p{i - 1}\n  then "-"\n  then 2 to 4 letter\n'
            f'  then optional "x"\n  then ("aa" or "bb" or "cc")\n  then exactly 3 digit\n'
        )
    return "\n".join(parts)


def independent_program(n: int) -> str:
    return "\n".join(
        f'pattern p{i}:\n  one or more letter\n  then "@"\n  then exactly 3 digit\n'
        f'  then ("com" or "org")\n'
        for i in range(n)
    )


def scalability(title: str, builder, sizes) -> None:
    heading(title)
    print(f"{'patterns':>9}{'tokens':>9}{'ms (mean of 5)':>16}{'peak KB':>10}")
    for n in sizes:
        source = builder(n)
        tokens = len(compile_source(source).tokens)
        print(f"{n:>9}{tokens:>9}{mean_ms(source, 5):>16.2f}{peak_kb(source):>10.0f}")


def main() -> None:
    print(f"EasyRegEx benchmark  |  Python {platform.python_version()}  |  {platform.system()}")
    sample_metrics()
    optimizer_effect()
    scalability("3. Scalability with named references (each pattern uses the previous one)",
                chained_program, [10, 50, 100, 200, 400])
    scalability("4. Scalability with independent patterns (no references)",
                independent_program, [100, 500, 1000, 2000])


if __name__ == "__main__":
    main()
