# Quick Start — tiferet-ly

This walkthrough runs the whole `Declare → translate → assemble → read`
journey end to end, against a small calculator language (addition and
multiplication) that is already declared and wired for you under
`configs/`. Every snippet below was run against the checked-in `configs/`
files from the repository root and its output transcribed verbatim — copy
and paste it as-is.

## 1. Point at the checked-in example application

Nothing here needs to be copied or edited by hand. The repository already
ships a working, wired application — `configs/app.yml` — pointed at the
sibling declared-language files (`configs/tokens.yml`,
`configs/productions.yml`, `configs/grammars.yml`). Run everything below
from the repository root:

```python
from tiferet import App

app = App('tiferet_ly', app_config='configs/app.yml')
```

## 2. Lex

`lex.default` tokenizes text against a declared grammar. Run it against
`'1+2*3'`:

```python
lexemes = app.run('lex.default', data={'grammar_id': 'arith', 'text': '1+2*3'})
for lexeme in lexemes:
    print(lexeme)
```

Output:

```
LexemeAggregate(type='NUMBER', value=1, lineno=1, lexpos=0)
LexemeAggregate(type='PLUS', value='+', lineno=1, lexpos=1)
LexemeAggregate(type='NUMBER', value=2, lineno=1, lexpos=2)
LexemeAggregate(type='TIMES', value='*', lineno=1, lexpos=3)
LexemeAggregate(type='NUMBER', value=3, lineno=1, lexpos=4)
```

Five lexemes, no `WS` lexeme in the sequence — the declared `WS` token
matches and discards whitespace, it never reaches the returned list.

## 3. Parse, raw

`parse.default` against the same text, with `render_result` absent,
returns the raw `AstNodeAggregate` the grammar's actions built:

```python
tree = app.run('parse.default', data={'grammar_id': 'arith', 'text': '1+2*3'})
print(repr(tree))
```

Output:

```
AstNodeAggregate(kind='add', children=[AstNodeAggregate(kind='num', children=[], value=1, lineno=None, lexpos=None), AstNodeAggregate(kind='mul', children=[AstNodeAggregate(kind='num', children=[], value=2, lineno=None, lexpos=None), AstNodeAggregate(kind='num', children=[], value=3, lineno=None, lexpos=None)], value=None, lineno=None, lexpos=None)], value=None, lineno=None, lexpos=None)
```

Notice the tree's own shape: the outermost node is `add`, and its second
child is a nested `mul` node holding `2` and `3` — multiplication binds
tighter than addition even though `configs/productions.yml` declares no
precedence table at all. `expr : expr PLUS term` / `term : term TIMES
factor` / `factor : NUMBER` layering disambiguates this by grammar
structure alone, the same approach `tiferet-takwin`'s own hand-written
parser uses.

## 4. Parse, rendered

The same call, with `render_result: True`, returns
`AstNodeAggregate.format()`'s string instead of the object — but it is
rendering the *same* underlying tree from step 3, not a second parse:

```python
rendered = app.run(
    'parse.default',
    data={'grammar_id': 'arith', 'text': '1+2*3', 'render_result': True},
)
print(rendered)
```

Output:

```
add
  num 1
  mul
    num 2
    num 3
```

`rendered == tree.format()` holds — `render_result` only chooses whether
`parse.default`'s last step formats the tree before returning it. This is
the same flag `configs/cli.yml`'s `parse` command exposes as
`--render-result`; there is no separate CLI-only mechanism, both paths
set the identical `render_result` Feature parameter.

## 5. Read more

- [Domain Vision Statement](domain-vision.md) — what tiferet-ly is for:
  declaring a language instead of hand-wiring it.
- [Core Domain Distillation](core-domain-distillation.md) — the
  vocabulary used above (declared language, grammar composition, action
  shorthand, rewrite table) defined precisely.
