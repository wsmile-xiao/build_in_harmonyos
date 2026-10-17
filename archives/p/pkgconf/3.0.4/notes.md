# pkgconf 3.0.4 adaptation notes

## Scope

- Activity: dependency (积分赛-依赖项), claimed by calbee21.
- Branch: `feat/pkgconf-3.0.4`.
- Source: official `pkgconf-3.0.4.tar.xz` release archive.
- Source SHA256: `91ce346b47f46b87d680c6928e6c43240b9cdc7a31afbea19f2298de4dbe266d`.
- Build system: Meson.
- External Conan dependencies: none (W0 preflight passed with zero deps).
- Status: published; local build, complete upstream suite, consumer
  compile/link, and command-runtime tests pass on this device.

## Relationship to the archived 3.0.5 recipe (W0b verification)

This adaptation reuses the validated recipe architecture and the seven
portability patches from the archived `archives/p/pkgconf/3.0.5` series.
Before starting, the 3.0.5 notes were read and every decision was re-checked
against the 3.0.4 release:

1. The 3.0.4 and 3.0.5 sources differ only in the release version string, two
   additional libc function probes in 3.0.5 (`getc_unlocked`, `mkdtemp`), and
   upstream source/test additions that exist only in 3.0.5. The build and test
   scaffolding the patches modify is byte-identical between the two releases.
2. All seven patches from the 3.0.5 series apply cleanly (`git apply 7/7`)
   to the pristine 3.0.4 release archive; the patched 3.0.4 meson test
   inventory equals 3.0.5 exactly (33 tests, identical names, including
   `fuzz-replay-missing-path`).
3. The historical 3.0.5 success ran in this same environment semantics:
   meson + ninja from the worker PATH (profile buildenv), clang 15.0.4 from
   `/data/service/hnp/bin`, and the `llvm-ar`/`llvm-ranlib` resolution from
   Conan's `tools.build:compiler_executables`. Every command in the 3.0.5
   notes is literally executable here, so the environment conclusions
   transfer (CI matrix row: gcc/clang/make/cmake/ninja/meson = available).
4. Version-specific inventory values were NOT carried forward from 3.0.5:
   fixtures were recounted for 3.0.4 (394 keys, not 425), the parser corpus
   was recounted (128 `.pc` inputs, not 141), and the solver corpus remains
   3 inputs. The conanfile validation constants and MANIFEST.yml reflect the
   recounted 3.0.4 numbers.

## Build decisions

- Build `libpkgconf` statically (R26: no shared `libpkgconf.so` that could
  collide with any system copy; the package installs an independent
  `libpkgconf.a` plus four command executables under the Conan package
  prefix only).
- Build a separate, uninstalled shared validation tree so linker wrapping
  stays outside `libpkgconf`; never package artifacts from that tree.
- When libc lacks `reallocarray`, provide the overflow-safe replacement only
  to allocation-failure test executables through an opt-in Meson option.
- Install the four upstream commands: `pkgconf`, `bomtool`, `spdxtool`, and
  `pccritic` (R38 commands.json declared at the software level).
- Do not create a `pkg-config` alias because upstream 3.0.4 does not install
  one.
- Resolve `llvm-ar` and `llvm-ranlib` from Conan's configured clang path,
  preserving compiler version suffixes and failing when the tools are absent.
- Build and test with one job/process to limit CPU use.
- Run the complete Meson suite from `build()` with a private writable `TMPDIR`
  (E002-class mitigation; `/tmp` is read-only on OHOS workers).
- Route API-test anonymous streams through the TMPDIR-aware `test_tmpfile()`
  helper from patch 0007 whenever `TMPDIR` is set (the libc `tmpfile()`
  ignores `TMPDIR` and returns NULL on read-only-`/tmp` workers).
- `can_run()` gates only target execution; CI workers without
  `llvm-objcopy`/`llvm-readelf`/`binary-sign-tool` still get the complete
  compile/link verification and the upstream suite, with an explicit
  `NOT_RUN` marker for runtime-only steps.

## Source changes

The seven patches are identical to the validated 3.0.5 series:

1. `fuzzer/parser-fuzzer.c` uses `TMPDIR` and aborts when temporary-file
   infrastructure fails, so a read-only `/tmp` cannot produce a false pass.
2. `fuzzer/replay.c` fails closed for filesystem and allocation errors,
   rejects empty corpora and truncated paths, and prints
   `REPLAYED_INPUTS=<count>`.
3. `fuzzer/solver-fuzzer.c` uses `TMPDIR`, propagates open/write/close
   errors, treats zero-byte writes as `EIO`, and aborts on infrastructure
   failures.
4. `meson_options.txt` adds a default-off validation switch for the test-only
   `reallocarray` shim.
5. `tests/api/reallocarray-shim.c` supplies an overflow-safe implementation
   only to OOM and corpus replay executables when the switch is enabled.
6. `meson.build` uses a target-link `--wrap=calloc` semantic probe rather
   than a host operating-system name, preserves the shared OOM boundary, and
   registers a missing-corpus negative test.
7. `tests/api/test-api.h` adds a test-only `TMPDIR`-aware anonymous stream;
   seven existing `tmpfile()` calls in audit, buffer, and file-I/O tests use
   it without any OHOS-specific conditional macro.

## Test inventory (3.0.4 release, recounted)

- 15 API executables: 14 entries from `api_tests` plus `api-serialize`.
- 14 fixture suites containing 394 independent `.test` files
  (3.0.5 has 425; the 31 extra fixtures only exist in 3.0.5).
- The canonical fixture result map contains 394 unique `(suite, fixture)`
  keys: 390 real `PASS` terminals plus 4 `SKIP` terminals whose fixtures
  declare `SkipPlatforms: unix haiku lite` (all four are Windows-oriented
  sysroot cases); zero fail.
- Capability permitting: one OOM API test, two corpus replay tests, and one
  missing-path negative replay test are registered (33 meson tests total).
- Parser corpus: 128 `.pc` inputs (127 in `tests/lib1/` plus 1 in
  `tests/lib1/child-prefix/pkgconfig/`). Solver corpus: 3 inputs.
- Symlink suite: 24 cases.

## Validation

- Upstream tests: 33/33 meson tests green (32 OK + 1 EXPECTEDFAIL for the
  missing-corpus negative, bound to return code 1, `REPLAYED_INPUTS=0`, and
  the missing-path stderr marker). Fixture terminals: 390 PASS + 4 SKIP,
  exactly matching the source-side `SkipPlatforms` map (0 mismatch).
  `fuzz-replay-parser` printed `REPLAYED_INPUTS=128`; `fuzz-replay-solver`
  printed `REPLAYED_INPUTS=3`. Total official inventory on this release:
  555/555 (100%).
- Local W3 `conan create` (ohos-aarch64 profile, static) completed; the
  recipe rebuilds the validation tree from the patched source, introspects
  the 33-test inventory, compiles 23 dependency-selected targets, runs the
  full suite inside a private writable TMPDIR, verifies every fixture
  terminal against the source map, and packages the four AArch64 ELF
  commands plus `libpkgconf.a`.
- The consumer test compiles and links against `libpkgconf.a` (12 API
  assertions on version constant 30004, version string 3.0.4, version
  comparison, `pkgconf_path_split`, and list cleanup) and exercises all four
  commands against a real `.pc` fixture (14 CLI assertions: `--version`
  reports 3.0.4 for each command; `--modversion`/`--cflags`/`--libs`
  resolution; bomtool SPDX-2.2 output; spdxtool SPDX 3.0.1 JSON-LD shape;
  pccritic 100/100 (A) grade). 26/26 assertions passed on this device where
  signing tools are present.
- The package contains four AArch64 ELF commands, a static library, five
  public headers, `libpkgconf.pc`, `pkg.m4`, and no `pkg-config` alias.
---

**编译结束**: 2026-09-03 18:37
**最终状态**: published
