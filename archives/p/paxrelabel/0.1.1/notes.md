# paxrelabel 0.1.1 adaptation notes

## Build environment

- Build system: raw Makefile
- Compiler: Conan profile C compiler (`tools.build:compiler_executables.c`)
- Status: built
- Build date: 2026-07-30

## Build steps

The recipe downloads the Alpine distfiles source archive for upstream tag
`v0.1.1`, applies one portability patch, and runs:

```bash
make -C <source> CC=<profile compiler> CFLAGS="<build_type flags> -fPIC -Wall -std=gnu2x -pedantic" -j1
```

The resulting `paxrelabel` executable is packaged under Conan `bin/`.

## Issues and fixes

| # | Issue | Root cause | Fix |
|---|---|---|---|
| 1 | Native Linux builds lack `strlcpy`; `alloca` is also less portable. | Upstream is written for libc environments that provide BSD helpers. | Replace the temporary target copy with `malloc`/`memcpy` and free it after `relabel_file`. |
| 2 | Runtime tests need deterministic rule directories. | Upstream search path is compile-time only. | Preserve the default path but allow `PAXRELABEL_SEARCH_PATH` to override it during tests. |

## Dependencies

No build or runtime Conan dependencies.

## Upstream tests

The exact release archive contains no upstream test suite. Inventory checked:

- `Makefile`
- `paxrelabel.c`
- `README.md`
- `COPYING`
- `.gitignore`
- `.gitlab-ci.yml`

Upstream tests: not applicable (0 cases).

## Verification plan

The `test_package` executes the packaged `paxrelabel` binary with controlled
rule directories:

- Missing rule directory: succeeds and reports zero relabeled files.
- Comment-only rule file: succeeds and reports zero relabeled files.
- Valid rule pointing to a missing target: succeeds and reports one relabeled
  file, exercising rule parsing and ENOENT handling.
- Invalid flag rule: exits non-zero and reports the invalid flag.

