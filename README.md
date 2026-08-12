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

## Documentation
This project has no implementation yet. Before writing code, start with:
- [Domain Vision Statement](docs/domain-vision.md) — what tiferet-ly is for
  and the value it aims to provide.
- [Core Domain Distillation](docs/core-domain-distillation.md) — the
  technical breakdown of its intended vocabulary, behaviors, and design
  commitments.
- [AGENTS.md](AGENTS.md) — orientation for contributors and AI agents
  working in this repository.
