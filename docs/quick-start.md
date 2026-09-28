# Quick-Start

Run the snippets below from the repository root, after installing this
package into the active environment:

```bash
pip install -e .
```

The checked-in calculator is addition and multiplication only. It has no
precedence table. `expr`, `term`, and `factor` layer the grammar so
multiplication binds tighter than addition.

## Point at the checked-in example application

`configs/app.yml` is a checked-in Tiferet application. It already points
`di.yml` at the sibling catalogues `configs/tokens.yml`,
`configs/productions.yml`, and `configs/grammars.yml`. Do not copy or edit
those files.

```python
from tiferet import App

app = App('example', app_config='configs/app.yml')
```

`example` is the session id declared in `configs/app.yml`. `App` reads that
file and resolves the catalogue services with no path override.

## Lex

```python
lexemes = app.run(
    'lex.default',
    data={'grammar_id': 'arith', 'text': '1+2*3'},
)
print(repr(lexemes))
```

```text
[LexemeAggregate(type='NUMBER', value='1', lineno=1, lexpos=0), LexemeAggregate(type='PLUS', value='+', lineno=1, lexpos=1), LexemeAggregate(type='NUMBER', value='2', lineno=1, lexpos=2), LexemeAggregate(type='TIMES', value='*', lineno=1, lexpos=3), LexemeAggregate(type='NUMBER', value='3', lineno=1, lexpos=4)]
```

The sequence is `NUMBER`, `PLUS`, `NUMBER`, `TIMES`, `NUMBER`. No `WS`
token is present. `WS` is declared to return `None`, which skips it. The
`NUMBER` action coerces the token value to `int` before the parse step uses
it. A lexeme stores that value as text, so the printed values are strings.

## Parse, raw

The same text, with `render_result` omitted, returns the parse object
itself. Print `repr`, not `format()`.

```python
raw = app.run(
    'parse.default',
    data={'grammar_id': 'arith', 'text': '1+2*3'},
)
print(repr(raw))
```

```text
AstNodeAggregate(kind='add', children=[AstNodeAggregate(kind='num', children=[], value=1, lineno=None, lexpos=None), AstNodeAggregate(kind='mul', children=[AstNodeAggregate(kind='num', children=[], value=2, lineno=None, lexpos=None), AstNodeAggregate(kind='num', children=[], value=3, lineno=None, lexpos=None)], value=None, lineno=None, lexpos=None)], value=None, lineno=None, lexpos=None)
```

The tree is an `add` whose second child is a `mul`. That nesting comes from
the grammar's own layering, not from a precedence declaration. The leaf
values are the integers the `NUMBER` action produced.

## Parse, rendered

The same call with `render_result: True` returns `format()` for that same
tree. It does not build a second object.

```python
rendered = app.run(
    'parse.default',
    data={
        'grammar_id': 'arith',
        'text': '1+2*3',
        'render_result': True,
    },
)
print(rendered)
```

```text
add
  num
  1
  mul
    num
    2
    num
    3
```

`rendered` is that string. It is `raw.format()`, not a different tree.
`configs/cli.yml` maps `--render-result` onto this same feature flag. It is
not a separate CLI-only mechanism.

## Link out

- [Domain vision](domain-vision.md) — why a small language is declared
  instead of hand-wired.
- [Core domain distillation](core-domain-distillation.md) — the declared
  language, how a grammar is composed, and the translation step that turns
  an action shorthand such as `$ast` into the rewrite the reader runs.
