# psutils 1.17 adaptation notes

## Scope

- Package: psutils/1.17
- Issue: #434
- Source: Debian snapshot of the original 1.17 tarball.

## Adaptation

- Added a Conan makefile recipe for the legacy upstream Makefile.
- Builds the C utilities with OHOS clang.
- Uses the Conan-selected C compiler and the upstream-compatible GNU C89
  language mode required by the 1997 sources.
- Generates Perl/shell helper scripts and manual pages using upstream `maketext`.
- Overrides install directories directly because upstream Makefile does not support `DESTDIR`.
- Signs only the six binaries listed by upstream Makefile variable `BIN`; the
  source archive contains a corresponding `.c` file for each entry, including
  `epsffit.c`.
- Verifies the ELF magic before invoking the OHOS binary signing tool, so a
  script can never be signed accidentally.

## Tests

- The exact 1.17 source archive has no test directory, registered runner, or
  Makefile check/test target.
- Added a `test_package` smoke test for the packaged command set.
- The test checks key binaries and resources, then verifies `psselect -?` reports usage without requiring PostScript input.

## Local Validation

- `python -m py_compile` was run for recipe/test files.
- `git diff --check` passed.
- Linux x86_64 `conan create`, Release: passed.
- Added consumer test: 1/1 passed; 10/10 assertions passed.
- The local Docker preflight is not an official OHOS armv8 CI result.
