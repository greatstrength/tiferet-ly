# AGENTS.md — tiferet-ly

## Project Overview

**tiferet-ly** is a [Tiferet](https://github.com/greatstrength/tiferet)-based
wrapper around [PLY](https://github.com/dabeaz/ply) (Python Lex-Yacc). It
lets a small language's vocabulary and grammar be declared rather than
hand-wired into PLY's own code-shaped conventions, without changing what PLY
itself is capable of recognizing.

- **Repository:** https://github.com/greatstrength/tiferet-ly
- **Branch:** `main`
- **Python:** ≥ 3.10 (matches the `tiferet` framework's own minimum)
- **Status:** Pre-implementation. No package code, `pyproject.toml`, or
  dependency declarations exist yet — only this file, the README, and the
  two documents below.

## Start here

This repository has no code yet, so there is no architecture section to read
in this file. Before doing anything else, read:

1. [docs/domain-vision.md](docs/domain-vision.md) — what tiferet-ly is for
   and the value it aims to provide, in plain language.
2. [docs/core-domain-distillation.md](docs/core-domain-distillation.md) —
   the technical breakdown: the domain's vocabulary, its four-step
   `Declare → translate → assemble → read` pipeline, its axes of variation,
   and its relationship to both PLY and the `tiferet` framework.

Section 10 of the distillation document ("Where this leads") names the
concrete TRDs that need to be written and approved before any of this
component's code is implemented. Do not start implementation work ahead of
that sequence.

## Contributing

1. Tie all work to a GitHub issue.
2. Write a TRD before any non-trivial change — see
   `docs/core-domain-distillation.md`, Section 10, for the known candidate
   TRDs this component still needs.
3. A code style has not been established yet, since no implementation
   language conventions have been introduced in this repository. Propose
   and record one (likely following the core `tiferet` framework's
   structured code style, since this component is built on it) as part of
   the first implementation TRD, rather than assuming it implicitly.
4. Keep functional changes and documentation/config changes in separate
   commits.
5. Include a `Co-Authored-By: Oz <oz-agent@warp.dev>` line on any commit
   made with AI agent collaboration.
6. Never commit or merge unless explicitly asked to.
