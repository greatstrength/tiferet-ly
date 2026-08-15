# Domain Vision Statement — Tiferet-Ly (Lex/Yacc Wrapper)

**Status:** Draft · **Domain:** `tiferet-ly` · **Code:** `tiferet_ly/` · **Branch:** `v1.x-proto`

## The bet: a small language's rules should be declared, not hand-wired into code
Most tools that read a made-up language — a configuration format, a command
syntax, a tiny scripting dialect — are built by hand: a programmer writes one
function per word the language recognizes and one function per sentence
pattern it accepts, scattered across a file that only grows as the language
grows. The rules of the language and the code that enforces them become the
same thing, so changing what the language accepts means finding and editing
code that already works.

Tiferet-Ly takes Tiferet's usual bet and applies it here: describe what a
small language looks like — its words and the patterns those words are
allowed to form — as data, and let a small, well-tested piece of machinery
turn that description into a working reader. The reading itself is not
reinvented; it rests on Python's own long-established Lex/Yacc library
(PLY), a widely used, freely available engine that already knows how to
recognize words and sentence patterns reliably. Tiferet-Ly's job is to let
that engine's own rules be declared the Tiferet way instead of hand-written
the way PLY normally expects.

## What this domain makes real
Tiferet-Ly is the component that lets someone describe a small language —
the words it's built from and the sentence shapes it allows — as
configuration, and get back a working reader for text written in that
language, without hand-writing the low-level plumbing that Python's
Lex/Yacc library otherwise requires line by line.

## What we get for it
**Add a word or a sentence pattern without touching code that already
works.** Because the language's rules live in a declared list rather than a
growing file of hand-written functions, adding a new keyword or a new way of
writing a sentence is an edit to that list — not a new function inserted
into, and tested against, a file shared by every rule that came before it.

**Test the reader without needing the real engine.** Tiferet wraps every
piece of outside infrastructure — a database, a file format — behind a small
contract it owns, so the business logic that depends on it can be tested
against a stand-in. Tiferet-Ly extends that same discipline to the Lex/Yacc
engine itself: a test can hand the wrapper a fake reader and confirm the
right rules were assembled, without ever invoking the real underlying
library.

**One place that says, exactly, what a language accepts.** Because every
word and sentence rule is catalogued the same way, answering "what is this
language allowed to contain" doesn't require reading through a module of
similarly named functions to reconstruct the answer by hand — the catalogue
already is the answer.

**The same wrapper serves many small languages, not just one.** A tiny
command syntax, a custom data-file format, a one-off scripting dialect for a
single application — each is just another declared catalogue read by the
same reading machinery, rather than a reason to write a new one from
scratch.

**Complexity stays where it's earned.** Most words and sentence patterns in
a small language are simple to recognize and need no special handling; a few
need a bit of custom logic to do something useful once recognized.
Tiferet-Ly keeps those two cases separate, so a simple rule stays a one-line
declaration and never has to carry the extra weight that only the
complicated rules actually need.

**A tree is available, never required.** Some languages want the reader to
hand back a tree of recognized sentences; some just want a number or a list.
Tiferet-Ly ships a small, generic tree a declaration can name with a short
spelling (`$ast`), the same kind of documented shorthand the rest of Tiferet
already uses for environment and request values. A language that already has
its own tree keeps it. A language that does not want a tree never mentions
one.

## The core of the work
Every language Tiferet-Ly reads goes through the same three-part journey:

> **Declare** a language's words and sentence patterns as data → **translate**
> that declaration into the exact form the underlying Lex/Yacc engine
> requires → **read** text written in that language and hand back a
> structured result.

The translation step is the one piece of real engineering here, and it
exists for a specific reason: PLY expects its rules written a particular
way — as small functions and values arranged according to strict, sometimes
unforgiving conventions of its own. Tiferet-Ly's design commitment is that a
person declaring a language should never have to know those conventions by
heart; the wrapper's job is to hold that knowledge on their behalf and
produce exactly what the engine expects, every time. So the shape underneath
everything is: **one translator, any declared language** — the translation
machinery is built once, and what varies from one use of Tiferet-Ly to the
next is never that machinery, only what has been declared to it.

## What it deliberately does not do
Tiferet-Ly does not invent a new way of matching words or sentence patterns,
and it does not change what the underlying Lex/Yacc engine is capable of
recognizing. It exposes that engine's own rules as something declared
instead of hand-written; it does not compete with or replace the engine
underneath it.

It does not decide what a recognized sentence *means*, or require that the
result be a tree. It offers a generic tree for languages that want one and
do not already have their own; it does not wrap a result that did not ask
to be a tree, and it does not take over the tree of a language that already
owns one. Whatever should be done with the result once produced belongs to
whoever declared that language and consumes Tiferet-Ly's output.

It has no opinion about which language is being declared. Whether the
language being read is a tiny command syntax, a data format, or something
built for a single one-off tool is a decision made entirely by whoever
writes the declaration — Tiferet-Ly's only concern is turning that
declaration into a working reader.

---

*Companion document:* `docs/core-domain-distillation.md` — the detailed
walkthrough of the domain's vocabulary, behaviors, and the relationships
between its parts.
