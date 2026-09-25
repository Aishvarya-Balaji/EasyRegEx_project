# EasyRegEx

A domain-specific language that compiles human-readable pattern
descriptions into standard regular expressions.

Instead of writing this:

```
^[a-zA-Z0-9]+@[a-zA-Z]+\.(?:com|org|in)$
```

you write this:

```
pattern email:
  one or more letter_or_digit
  then "@"
  one or more letter
  then "."
  then ("com" or "org" or "in")
```

and the compiler produces the regular expression for you, after checking
it for errors.

---

## Quick start

```bash
# compile a file and run its declared test cases
python main.py inputs/email.rx

# see every stage of the compiler
python main.py inputs/email.rx --all

# try a string against the compiled patterns
python main.py inputs/email.rx --match "alice@example.com"

# run the test suite
pip install pytest
python -m pytest tests/ -v
```

Optional web interface:

```bash
pip install flask
python app.py          # then open http://127.0.0.1:5000
```

---

## The compiler pipeline

| Phase | Module | Input | Output |
|-------|--------|-------|--------|
| 1. Lexical analysis | `easyregex/lexer.py` | `.rx` source text | token stream |
| 2. Syntax analysis | `easyregex/parser.py` | token stream | abstract syntax tree |
| 3. Semantic analysis | `easyregex/semantic.py` | AST | validated AST + symbol table |
| 4. Optimization | `easyregex/optimizer.py` | AST | simplified AST |
| 5. Code generation | `easyregex/codegen.py` | AST | regular expression |
| 6. Test execution | `easyregex/testrunner.py` | regex + test cases | pass / fail report |

`easyregex/compiler.py` runs the phases in order; `main.py` is the
command-line front end and `app.py` the optional web front end.

---

## Language reference

### Pattern definitions

```
pattern <name>:
  <rule>
  then <rule>
  ...
```

`then` is optional and exists only for readability. A pattern body runs
until the next `pattern` or `test` block, or the end of the file.

### Rules

| Written as | Meaning | Compiles to |
|-----------|---------|-------------|
| `"text"` | match exactly | `text` (escaped) |
| `digit` | one digit | `[0-9]` |
| `letter` | one letter | `[a-zA-Z]` |
| `letter_or_digit` | one letter or digit | `[a-zA-Z0-9]` |
| `whitespace` | one whitespace character | `\s` |
| `any` | any single character | `.` |
| `one or more X` | X, at least once | `X+` |
| `zero or more X` | X, any number of times | `X*` |
| `optional X` | X, or nothing | `X?` |
| `exactly N X` | X repeated N times | `X{N}` |
| `N to M X` | X repeated N to M times | `X{N,M}` |
| `(A or B or C)` | any one of A, B, C | `(?:A|B|C)` |
| `use <name>` | another pattern, inlined | that pattern's regex |

Comments start with `#` and run to the end of the line.

### Named references

A pattern can be defined once and reused:

```
pattern domain:
  one or more letter_or_digit
  then "."
  then ("com" or "org")

pattern url:
  ("http" or "https")
  then "://"
  then use domain
```

References may appear before the pattern they refer to. Circular
references are rejected by the semantic analyzer.

### Test blocks

Expectations can be declared in the source file itself and are run by the
compiler:

```
test email:
  match "alice@example.com"
  reject "no-at-sign.com"
```

`match` means the pattern must accept the string; `reject` means it must
not. Generated patterns are anchored with `^` and `$`, so a match means
the whole string conforms.

---

## Errors the compiler catches

| Error | Phase | Example |
|-------|-------|---------|
| Unexpected character | Lexer | `then $` |
| Unterminated string | Lexer | `"abc` |
| Missing colon, unclosed group | Parser | `pattern p` |
| Empty pattern body | Parser | `pattern p:` with nothing after it |
| Duplicate pattern name | Semantic | two `pattern code:` blocks |
| Undefined reference | Semantic | `use domain` with no such pattern |
| Circular reference | Semantic | `a` uses `b`, `b` uses `a` |
| Invalid repetition range | Semantic | `5 to 2 digit` |
| Test for an undefined pattern | Semantic | `test missing:` |

Every message reports the line and column. Semantic errors are collected
and reported together rather than one at a time.

Sample broken files are in `inputs/errors/`, one per error type:

```bash
python main.py inputs/errors/circular_reference.rx
```

---

## Project structure

```
easyregex_project/
├── main.py                     command-line interface
├── app.py                      optional Flask web interface
├── easyregex/
│   ├── __init__.py
│   ├── errors.py               error types shared by all phases
│   ├── tokens.py               token types, keywords, character classes
│   ├── lexer.py                Phase 1: lexical analysis
│   ├── ast_nodes.py            AST node definitions and tree printing
│   ├── parser.py               Phase 2: recursive-descent parser
│   ├── semantic.py             Phase 3: symbol table and validation
│   ├── optimizer.py            Phase 4: AST simplification
│   ├── codegen.py              Phase 5: regex generation
│   ├── testrunner.py           Phase 6: running declared test cases
│   └── compiler.py             pipeline driver
├── inputs/
│   ├── email.rx  phone.rx  username.rx
│   ├── url.rx  date.rx  identifier.rx
│   └── errors/                 one file per error type
└── tests/
    ├── test_lexer.py
    ├── test_parser.py
    ├── test_semantic.py
    ├── test_codegen.py
    └── test_integration.py
```

---

## Grammar (BNF)

```
program      ::= { pattern_def | test_block }

pattern_def  ::= "pattern" IDENT ":" body
body         ::= { [ "then" ] term }

term         ::= quantified | atom
quantified   ::= "one" "or" "more" atom
               | "zero" "or" "more" atom
               | "optional" atom
               | "exactly" NUMBER atom
               | NUMBER "to" NUMBER atom

atom         ::= STRING
               | CLASS
               | "use" IDENT
               | "(" alternative { "or" alternative } ")"
alternative  ::= term { [ "then" ] term }

test_block   ::= "test" IDENT ":" { test_case }
test_case    ::= ( "match" | "reject" ) STRING

CLASS        ::= "digit" | "letter" | "letter_or_digit"
               | "whitespace" | "any"
```

---

## Command-line options

| Option | Effect |
|--------|--------|
| *(none)* | show generated regexes and run declared tests |
| `--tokens` | show the token stream |
| `--ast` | show the abstract syntax tree |
| `--symbols` | show the symbol table |
| `--regex` | show the generated regular expressions |
| `--test` | run the declared test cases |
| `--all` | show every stage |
| `--no-optimize` | skip the optimizer, to compare its effect |
| `--match STR` | test one string against every pattern |

---

## Optimizations

The optimizer rewrites the AST before code generation:

1. **Constant folding** — adjacent literals merge: `"a" "b" "c"` becomes `"abc"`
2. **Sequence flattening** — nested sequences collapse into one
3. **Redundant group elimination** — `(X)` with a single alternative becomes `X`
4. **Redundant quantifier elimination** — `exactly 1 X` becomes `X`
5. **Single-element unwrapping** — a sequence of one item becomes that item

Use `--no-optimize` to see the unoptimized output and compare.
