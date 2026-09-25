"""EasyRegEx: a domain-specific language for human-readable regular expressions.

Pipeline:
    source (.rx)  ->  lexer      ->  token stream
    token stream  ->  parser     ->  abstract syntax tree
    AST           ->  semantic   ->  validated AST + symbol table
    AST           ->  optimizer  ->  simplified AST
    AST           ->  codegen    ->  regular expression
    regex + cases ->  testrunner ->  match / no-match results
"""

__version__ = "1.0"
