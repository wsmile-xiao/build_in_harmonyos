# Draft: Raw Makefile hardcoding CC:=g++ fails on OHOS — override on make command line

> Source event: `cohomcalg/0.32` first OHOS adaptation on 2026-09-08.
> Draft only. Do not promote to `knowledge/graph/` without reviewer assignment.

## Problem

`cohomcalg` 0.32's top-level Makefile hardcodes the C++ compiler:

```makefile
CC := g++
LD := g++
```

The OHOS PC toolchain provides clang/clang++ only (no g++), so the very first
object compile fails:

```text
make: g++: No such file or directory
make: *** [Makefile:65: build/iohandler.o] Error 127
```

Because this is a **raw Makefile** project (no `configure`/CMake), the autotools
workaround (export `CC`/`CXX` before configure) does not apply — and it would not
work anyway: `:=` in the Makefile overrides environment variables.

## Fix

Override the recipe variables on the make command line (command-line assignments
beat `:=` in the Makefile):

```bash
make -j1 CC=clang++ LD=clang++
```

GNU make jobserver must be disabled (`-j1`) on HMDFS/SELinux workers (mkfifo
denied — see the forbid clause in the `.kv`). Keep the upstream's own
`DEFS := -DPOLYLIB_BITS=64` untouched.

In a Conan recipe, resolve the compiler from
`self.conf.get("tools.build:compiler_executables", ...)` (R33) and run
`self.run(f'make -j1 CC="{cc}" LD="{cc}"', cwd=self.source_folder)`.

## Verification

- `make clean && make -j1 CC=clang++ LD=clang++` → exit 0, `bin/cohomcalg` (473600 B)
- 6/7 upstream samples pass; OHOS test 5/5; `conan create` + test_package PASS

## Applicability / Counter-examples

- Any raw-Makefile C/C++ project on OHOS whose Makefile hardcodes g++.
- Counter-example: configure/CMake-based projects → E053-style env override;
  Makefiles using `?=` (not `:=`) already honor the environment.

## Relations

- similar_to: [E053] (autotools CXX override; different trigger — configure vs raw make)
- Not caused by / prerequisite of existing entries; no conflict.

## Records

- success_count: 1, fail_count: 0, confidence: 0.85
- contributor: pc1-34