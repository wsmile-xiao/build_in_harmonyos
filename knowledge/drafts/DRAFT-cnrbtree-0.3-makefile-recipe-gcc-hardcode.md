# Draft: Raw Makefile embedding `gcc` in recipe bodies fails on OHOS — rewrite recipe to `$(CC)`

> Source event: `cnrbtree/0.3` first OHOS adaptation on 2026-09-22.
> Draft only. Do not promote to `knowledge/graph/` without reviewer assignment.

## Problem

`cnrbtree` 0.3's top-level Makefile hardcodes the C compiler **inside the
recipe bodies**, with no `CC`/`CXX` variable declared at all:

```makefile
testtree : testtree.c
	gcc -o $@ $^ -Os -g -Wall -Wno-unused-value -Wno-unused-function -Wextra -pedantic -fsanitize=address,undefined

simple : simple.c
	gcc -o $@ $^ -Os -g
```

The OHOS PC toolchain provides clang only (no `gcc`), so the first compile
fails immediately:

```text
make: gcc: No such file or directory
make: *** [Makefile:4: testtree] Error 127
```

## Why the usual workaround fails

For projects that declare the compiler as a Makefile **variable**
(e.g. `CC := g++` — see `DRAFT-cohomcalg-0.32-makefile-gxx-override`),
the GNU-make command-line override `make CC=clang++` works. But cnrbtree's
Makefile has **no compiler variable** — `gcc` is written literally in the
recipe. `make CC=clang` therefore has **no effect**: the recipe still invokes
`gcc` and still fails. The recipe itself must be rewritten.

## Fix

Edit each recipe to reference `$(CC)` instead of the literal compiler name,
then build with the compiler passed on the make command line:

```bash
# Makefile:
#   gcc ...  ->  $(CC) ...
make CC=clang testtree simple
```

In a Conan recipe, resolve the compiler from
`self.conf.get("tools.build:compiler_executables", ...)` (R33) and pass it on
the make command line; keep upstream's recipe flags (e.g.
`-fsanitize=address,undefined`) untouched. Use `-j1` on HMDFS/SELinux workers
(make jobserver mkfifo is denied).

## Verification

```bash
make CC=clang testtree simple        # rc=0
./testtree                           # rc=0, "OK"
./simple                             # rc=0
# W3 build_and_test.sh pass; conan create + test_package 1032 assertions PASS
```

## Boundary vs. existing knowledge

- `DRAFT-cohomcalg-0.32-makefile-gxx-override`: compiler declared as
  `CC := g++` variable → command-line override suffices, no patch needed.
- This entry: compiler embedded in recipe body, no variable → command-line
  override is inert; the recipe must be rewritten to `$(CC)` (patch).

Applies to any raw-Makefile C/C++ project whose rules call the compiler by
name instead of through `$(CC)`/`$(CXX)`.
