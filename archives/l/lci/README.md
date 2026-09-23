# lci

An interactive interpreter for pure (untyped) lambda calculus. lci parses
lambda terms with user-defined aliases and infix operators, normalizes them
(call-by-need with cycle detection), and pretty-prints results with a
graph-reduction engine. It ships a `.lcirc` prelude (church arithmetic, list
operations, fixed-point combinators) and a pure-lambda N-queens solver
(`queens.lci`). A C application built with CMake; the grammar is generated
at build time by the vendored `dparser` generator, and the interactive REPL
line editing comes from the vendored `replxx` (C++).

- Homepage: https://github.com/chatziko/lci
- License: GPL-2.0-only (dparser: BSD; replxx: BSD-3-Clause)
- Build system: CMake (single `lci` executable)
- Dependencies: none (vendored dparser + replxx, static)

## OHOS adaptation notes

- `cmake_minimum_required(3.3)` at the top level is accepted by CMake 4, but
  the vendored `dparser` subproject declares `cmake_minimum_required(3.0)`;
  `CMAKE_POLICY_VERSION_MINIMUM=3.5` is passed as a CMake **cache variable**
  (knowledge E187 / draft DRAFT-E321) so it is in effect before any
  `project()` call.
- `src/run.c` guards its System V `TCGETA`/`TCSETA` fallback defines with
  `#ifndef`: musl's `bits/ioctl.h` already defines both ioctls and has no
  `TIOCGETA`/`TIOCSETA`, which broke the build (patch 0001, portability).
- The build runs the just-compiled `make_dparser` grammar generator on the
  build host; on the OHOS PC self-hosted aarch64 environment this is a
  native execution, not a cross gap (no E359 host mapping needed). The same
  applies to running `ctest` against the build tree (E486/E489 signing).
- Terminal tool: linked statically, `BUILD_SHARED_LIBS=OFF` (R26).
- The packaged `bin/lci` consults its prelude from `<package>/share/lci/.lcirc`
  via the compile-time `DATADIR`, so it works from any working directory;
  `Consult 'queens.lci'` resolves relative to the current directory.
- Upstream CTest suite (`build`, `queens`, `fixed_point` — 3 cases, all
  functional) runs inside `conan create`; `test_package` re-verifies the
  installed interpreter through two test entries — `test_lci.sh` (1 entry;
  3 scenarios / 7 assertions: the upstream expressions plus prelude
  arithmetic) and `ohos_specific_test.py` (1 entry; 6 checkpoints: a real
  pseudo-terminal REPL session that actually executes the patched
  termios/replxx init path, plus ELF64-LE-AArch64 identity /
  musl-interpreter / `.codesign` / no-RPATH / no-build-path checks on the
  packaged binary, all fail closed).

## Versions

| Version | Status | Notes |
|---------|--------|-------|
| 1.1     | built  | v1.1 release tag, 2024-12-14; submodules pinned by the tag |
