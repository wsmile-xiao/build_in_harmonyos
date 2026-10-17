# Draft: C++11 user-defined-literal concat error under clang++

> Source event: `cohomcalg/0.32` first OHOS adaptation on 2026-09-08.
> Draft only. Do not promote to `knowledge/graph/` without reviewer assignment.

## Problem

Legacy C++ (or C files compiled in C++ mode) concatenating a string literal with a
macro identifier fails under clang++ with strict C++11 parsing:

```text
source/polylib_mod/matrix.c:153:21: error: invalid suffix on literal;
C++11 requires a space between literal and identifier [-Wreserved-user-defined-literal]
        value_print(Dst," "P_VALUE_FMT" ",*p++);
```

`cohomcalg` 0.32 is a sheaf-cohomology CLI (arXiv:1003.5217) with an embedded
modified PolyLib (`source/polylib_mod/`). Its Makefile compiles all `.c` sources
in C++ mode (`CC := g++`). Under old GCC this parsed as string concatenation;
clang++ 15 (C++11 strict) reads `" "P_VALUE_FMT` as a user-defined literal suffix
(`P_VALUE_FMT` expands to a printf format specifier like `%ld`).

## Fix

Insert a space between the closing quote and the macro identifier:

```diff
-	value_print(Dst," "P_VALUE_FMT" ",*p++);
+	value_print(Dst," " P_VALUE_FMT " ",*p++);
```

Macro expansion is unaffected — whitespace between string literals and tokens is
dropped before concatenation.

## Verification

- `make -j1 CC=clang++ LD=clang++` → exit 0, `bin/cohomcalg` produced
- 6/7 upstream `bin/*.in` samples pass (`--integrated --nomonomfile`); P31SU8 times out (10-dim GLSM, 41 SR-ideal terms — inherent compute cost, not a regression)
- OHOS-specific test `test_ohos_cohomology.sh`: 5/5 PASS
- `conan create` (ohos-aarch64): PASS incl. test_package consumer run

## Applicability / Counter-examples

- Applies to any legacy C/C++ moved to clang++/C++11-strict (numeric/polyhedral libs with
  printf-style macro concat are the typical hit).
- Counter-example: GCC lenient parsing, or code without macro-after-literal concatenation.

## Relations

- similar_to: [] (no existing graph entry covers this)
- Not caused by any existing entry; no conflict; not a prerequisite.

## Records

- success_count: 1, fail_count: 0, confidence: 0.9
- contributor: pc1-34
