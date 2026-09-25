import re
from dataclasses import dataclass

from .ast_nodes import Program

__all__ = ["TestResult", "TestReport", "run_tests", "match_string"]


@dataclass
class TestResult:
    pattern_name: str
    text: str
    expected_match: bool
    actual_match: bool
    line: int

    @property
    def passed(self) -> bool:
        return self.expected_match == self.actual_match

    def describe(self) -> str:
        verb = "match" if self.expected_match else "reject"
        status = "PASS" if self.passed else "FAIL"
        got = "matched" if self.actual_match else "did not match"
        return f"[{status}] {self.pattern_name}: {verb} {self.text!r} -> {got}"


@dataclass
class TestReport:
    results: list

    @property
    def passed(self) -> int:
        return sum(1 for r in self.results if r.passed)

    @property
    def failed(self) -> int:
        return sum(1 for r in self.results if not r.passed)

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def all_passed(self) -> bool:
        return self.failed == 0

    def summary(self) -> str:
        if self.total == 0:
            return "No test cases declared."
        if self.all_passed:
            return f"All {self.total} test cases passed."
        return f"{self.passed} of {self.total} test cases passed, {self.failed} failed."


def match_string(regex: str, text: str) -> bool:
    """Return True if the generated regex accepts the whole string."""
    return re.match(regex, text) is not None


def run_tests(program: Program, regexes: dict) -> TestReport:
    """Run every test case declared in the program against its pattern."""
    results = []

    for block in program.tests:
        regex = regexes.get(block.pattern_name)
        if regex is None:
            continue  # semantic analysis already reported this
        for case in block.cases:
            actual = match_string(regex, case.text)
            results.append(TestResult(
                pattern_name=block.pattern_name,
                text=case.text,
                expected_match=case.should_match,
                actual_match=actual,
                line=case.line,
            ))

    return TestReport(results)
