# tiferet-ly
A Lex/Yacc Wrapper built with Tiferet

## Overview
tiferet-ly lets you describe a small language — its words and the sentence
patterns it accepts — as a declared list instead of hand-written code. Hand
tiferet-ly that declaration and get back a working reader for text written in
that language, built on Python's well-established Lex/Yacc engine
([PLY](https://github.com/dabeaz/ply)). Adding a new keyword or sentence
pattern becomes an edit to the declaration rather than a new function buried
in a growing file, and the pieces around it can be tested without invoking
the real parsing engine at all.

## How it works
tiferet-ly runs every declared language through the same four-step
journey: **declare** a language's words and sentence patterns as YAML
catalogues (`tokens`, `productions`, `grammars`); **translate** each
declared rule into the literal function or string PLY's own conventions
require; **assemble** a lexer and parser for one grammar's effective rule
set; **read** text written in that language and hand back a structured
result — optionally a small, generic `AstNode` tree, rendered as a string
on request.

See [Quick Start](docs/quick-start.md) for a runnable, worked example (a
small calculator language) that walks through all four steps against the
checked-in `configs/` example application.

## Documentation
- [Quick Start](docs/quick-start.md) — a runnable, end-to-end example.
- [Domain Vision Statement](docs/domain-vision.md) — what tiferet-ly is for
  and the value it aims to provide.
- [Core Domain Distillation](docs/core-domain-distillation.md) — the
  technical breakdown of its intended vocabulary, behaviors, and design
  commitments.
- [AGENTS.md](AGENTS.md) — orientation for contributors and AI agents
  working in this repository.
