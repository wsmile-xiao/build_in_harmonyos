# libxtend 0.2.1 adaptation notes

## Status

- Added a Conan recipe for the upstream Makefile project.
- Built only the static `libxtend.a` target; shared library and manpage
  generation are not required by downstream `ad2vcf`.
- OHOS build patches `fast-file.c` for portable gzip decompression,
  zero `st_blksize` fallback, and EOF/error handling on `read()`.
- Consumer smoke validates `xt_strlcpy()` through installed headers and the
  packaged static library.

## Upstream Tests

The release includes 2 ad-hoc shell test entrypoints:

- `Test/test.sh`
- `Test/Fast-file/test.sh`

The recipe covers both entrypoints with CI-safe automated equivalents instead
of running the shell scripts verbatim:

- `Test/main-test.c` is compiled and executed.
- `Test/Fast-file/iotest-ffile.c` is compiled and used for uncompressed and
  gzip roundtrip checks, then `Test/Fast-file/hl-test.c` is compiled and run.

The literal scripts are not suitable for unattended OHOS CI as-is:

- `Test/test.sh` references a `./file` binary that is not produced by the
  release tarball test sources.
- `Test/Fast-file/test.sh` is interactive, downloads a FreeBSD ISO, performs
  large throughput checks, and asks for cleanup confirmation.

Build-local test source adaptations are applied only for CI execution:

- `hl-test.c` uses a build-local temporary filename instead of hard-coded
  `/tmp`.
- `hl-test.c` NUL-terminates the buffer after `xt_ff_read()` before `strcmp()`;
  `xt_ff_read()` is a binary read API and does not guarantee string
  termination.

## OHOS Validation

- Date: 2026-08-09, SSH port 33332, isolated job `ad2vcf-deps-upstream-20260809-r1`.
- Run dir: `/storage/Users/currentUser/ohos-test-runs/codex-a-libxtend-deps-upstream-libxtend-r9-20260809-055039-33587`.
- Full package reference: `libxtend/0.2.1#518375c9b2b56e3d5393a71846a836ff:f23d5a9b1d537641c03c7814478a2fadb727650a#30efeec57878d83467f040f1b7e7aae4`.
- CI gates: L0 pass, L1 pass, L2 skip (library package), L4 pass, L5 pass.
- Upstream test entrypoints covered: 2/2 recipe-level automated equivalents,
  passed 2/2. Added consumer smoke executed and passed.
