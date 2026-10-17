# pkgconf 3.0.5 adaptation notes

## Scope

- Dependency relationship: pkgconf provides the `pkg-config` build-tool entry
  consumed by the gcompat source build inside GraalVM 25.0.3 Issue `#1085`.
  Dependency Issue `#1694` owns this prerequisite adaptation.
- Activity: dependency.
- Branch: `feat/pkgconf-3.0.5`.
- Source: official `pkgconf-3.0.5.tar.xz` release archive.
- Source SHA256: `3acd3a8a3cce65a8d620321855d92fb602e026cbe8e13ee36bdec58483b59ace`.
- Upstream tag commit: `3086e5dfc16b8cf9a9b66f6827868af4aa85e9bd`.
- Build system: Meson.
- External Conan dependencies: none.
- Status: built; local build, upstream tests, local CI, and the exact-snapshot
  device run pass. Platform CI build #26630/buildid 29515 reached the complete
  upstream suite and exposed three API tests whose libc `tmpfile()` ignored the
  writable `TMPDIR`; patch 0007 repaired that boundary. Build #26988/buildid
  29985 then passed upstream 586/586 and consumer compilation/linking, but the
  Worker lacked the three signing tools required for target runtime. The
  artifact-first runtime capability gate has a 7/7 directed repair and
  replacement CI is pending.

## Build decisions

- Build `libpkgconf` statically without forcing a fully static libc link.
- Build a separate, uninstalled shared validation tree so linker wrapping stays
  outside `libpkgconf`; never package artifacts from that tree.
- When libc lacks `reallocarray`, provide the overflow-safe replacement only to
  allocation-failure test executables through an opt-in Meson option.
- Install the four upstream commands: `pkgconf`, `bomtool`, `spdxtool`, and
  `pccritic`.
- Do not create a `pkg-config` alias because upstream 3.0.5 does not install it.
- Resolve `llvm-ar` and `llvm-ranlib` from Conan's configured clang path,
  preserving compiler version suffixes and failing when the tools are absent.
- Build and test with one job/process to limit CPU use.
- Run the complete Meson suite from `build()` with a private writable `TMPDIR`.
- Run Meson JSON introspection through `self.run` in explicit `conanbuild`
  build scope. Bare Python subprocesses do not inherit the profile-provided
  build-tool PATH on minimal CI workers.
- Route API-test anonymous streams through a portable helper that uses
  `mkstemp + unlink + fdopen` whenever a nonempty `TMPDIR` is provided; retain
  the standard `tmpfile()` behavior on Windows and when no override exists.
- Treat `can_run()` as build/host compatibility rather than proof that an OHOS
  Worker has `llvm-objcopy`, `llvm-readelf`, and `binary-sign-tool`. Require the
  linked consumer and four command artifacts first; only an absent signing tool
  may produce an explicit runtime `NOT_RUN`, while the complete tool path keeps
  all 26 assertions and every other error remains fatal.

## Source changes

1. `fuzzer/parser-fuzzer.c` now uses `TMPDIR` and aborts when temporary-file
   infrastructure fails, so a read-only `/tmp` cannot produce a false pass.
2. `fuzzer/replay.c` now fails closed for filesystem and allocation errors,
   rejects empty corpora and truncated paths, and prints
   `REPLAYED_INPUTS=<count>`.
3. `fuzzer/solver-fuzzer.c` uses `TMPDIR`, propagates open/write/close errors,
   treats zero-byte writes as `EIO`, and aborts on infrastructure failures.
4. `meson_options.txt` adds a default-off validation switch for the test-only
   `reallocarray` shim.
5. `tests/api/reallocarray-shim.c` supplies an overflow-safe implementation only
   to OOM and corpus replay executables when the switch is enabled.
6. `meson.build` uses a target-link `--wrap=calloc` semantic probe rather than
   a host operating-system name, preserves the shared OOM boundary, and
   registers a missing-corpus negative test.
7. `tests/api/test-api.h` adds a test-only `TMPDIR`-aware anonymous stream;
   seven existing `tmpfile()` calls in audit, buffer, and file-I/O tests use it
   without any OHOS-specific conditional macro.

The patches are generated from an isolated work copy by
`refresh-patch --auto`. The pristine tree remains byte-identical to the
official release archive for all ten modified or added files.

The submitted unified-diff wrappers use nonblank source anchors and explicit
delete/add records for unchanged blank or Tab-indented lines. This keeps the
patches valid under the repository's outer whitespace check without weakening
hunk matching. Git apply, GNU patch 2.7.6 with `--fuzz=0`, and Conan patch_ng
all replayed the combined 7/7 patch series. Git with LF conversion disabled,
GNU patch 2.7.6 at `--fuzz=0`, and patch_ng produced byte-identical 755-file
post-images (inventory SHA256
`26dfcd9a2676e98f7ca293690d3f4587fdee3125b42b024c72b087610e6796c2`).
The tested post-image is strict UTF-8 CRLF-to-LF equivalent.

## Test inventory

- 15 API executables: 14 entries from `api_tests` plus `api-serialize`.
- 14 fixture suites containing 425 independent `.test` files.
- The canonical fixture result map contains 425 unique `(suite, fixture)` keys
  and binds exactly one real `PASS` terminal to every key, with zero skip/fail.
- Capability permitting: one OOM API test, two corpus replay tests, and one
  missing-path negative replay test are registered.
- Parser corpus: 141 `.pc` inputs. Solver corpus: 3 inputs.
- Symlink suite: 24 cases and 48 `SetupSymlink` operations.

The fixture and corpus counts were recalculated from the official 3.0.5 release
archive; no 3.0.4 inventory value is carried forward.

## Validation

- Upstream tests: 586/586 (100%). The inventory contains 15 API executables,
  425 fixture files, one OOM test, 141 parser corpus inputs, three solver
  corpus inputs, and one missing-corpus negative test.
- Hash-bound Meson logs registered the same 33 top-level tests and produced the
  unified 586/586 official inventory; the required negative is bound to
  `EXPECTEDFAIL`, return code 1, `REPLAYED_INPUTS=0`, and the missing-path
  stderr marker.
- The current seven-patch post-image completed the same official inventory at
  586/586. The three Buildbot failures (`api-audit`, `api-buffer`, and
  `api-fileio`) are all `OK`; the `test_tmpfile()` directed matrix passed 6/6,
  covered 7/7 call sites, and left no temporary-file residue. Formal knowledge
  entry E272 supplies the existing reusable `tmpfile()` boundary, so this CI
  repair does not create a duplicate knowledge draft.
- The fresh isolated r20 OHOS/arm64 semantic-baseline `conan create` completed with RREV
  `4a3f062deb7823efabd171c60b7aab22`, package ID
  `21b17f8b2bc0e9511e276e3d57a23893067cefe5`, and PREV
  `7dad25c18ecf6400f17f94e2df9542ce`. It exported all seven patches,
  compiled 43 primary and 125 validation targets, packaged the same binary
  revision, and cross-compiled the consumer; log SHA-256 is
  `06c0a7ff041987ac4c64c4c391e1f7aea39f7382a2ca844ed4abe7e8b3f5833d`.
  The submitted outer-safe 0007 wrapper has SHA-256
  `911c89e722683f216e8baea4b23c76e14be324660f09793d6b0cbf907025e7fa`;
  Git, GNU patch `--fuzz=0`, and patch_ng reproduce the baseline's exact
  755-file post-image.
- The separate shared validation tree joined 23/23 Meson dependency IDs to
  unique `name:executable` selectors, including every command invoked by the
  fixture runner, while the package installed only `libpkgconf.a`.
- The overflow negative probe returned `ENOMEM`; the static-boundary negative
  build reproduced `TEST_ASSERT_NULL(a)` while the shared validation build
  passed, proving the fix depends on the intended link boundary.
- The 19/19 result-gate matrix rejected unexpected PASS/SKIP/FAIL terminals,
  missing or duplicate fixture rows, expected-failure drift, and invalid target
  projections. The exact `shared=True` graph is `info_invalid`.
- The package contains four AArch64 ELF commands, a 21-object static library,
  five public headers, `libpkgconf.pc`, and no `pkg-config` alias.
- Local CI passed 1/1 with L0, L1, L1e, and L5 successful. L4 emitted only its
  known substring false positive because unchanged comments contain `targets`
  (ending in `gets`); no dangerous call was added.
- Exact-current-HEAD Buildbot build #26332, buildid 29163, downloaded the
  source, compiled all 43 primary targets, and completed the shared validation
  setup before bare `subprocess.run(["meson", ...])` failed with
  `FileNotFoundError`. The repaired production methods use the same Conan
  build scope as the successful setup commands; their directed matrix passed
  13/13, including empty host PATH, nonzero, JSON, inventory, and target
  projection negatives.
- Exact-current-HEAD Buildbot build #26630, buildid 29515, then proved source
  retrieval, all 43 primary targets, all 125 validation targets, and Meson
  execution before three libc `tmpfile()` calls returned `NULL`. The new helper
  honors the already-created writable test directory while preserving
  anonymous-file cleanup.
- Exact-current-HEAD Buildbot build #26988, buildid 29985, passed source
  retrieval, 43/43 primary targets, 125/125 validation targets, upstream
  586/586, package creation, and consumer compilation/linking. Its only failure
  occurred before runtime because the Worker had none of the three required
  signing tools. The repaired production entry passed 7/7 directed cases for
  missing tools, complete tools, missing consumer, missing command,
  no-execution-on-skip, and both `can_run(false)` artifact-order boundaries;
  current-HEAD replacement CI remains pending.
- The 26 added consumer assertions compile and link against the exact package.
  The endpoint-215 r36 transaction executed all 26/26 against candidate tree
  `0a17ebc2b9c6dc8add9eebc42be8bbe73805d0cf`, with one controller launch, one
  runner launch, runner RC 0, and five signed ELF inputs.
- The sealed release returned root-process count 0, two clean scans, and absent
  lock/lease; postrelease passed. The 1,427,968-byte readback tar has SHA-256
  `83856bf764a71f75d59755b3c88047337a0b66b6c5fb27e829f33fcb64bbc7fb`.
- The consumed host controller rejected only the expected archive-root
  directory record after W3 and release had passed. A create-new postrelease
  validator accepted the exact 12 directories, 36 regular files, and 13/13
  evidence hashes; its directed positive/negative matrix passed 7/7. The
  reconciliation result SHA-256 is
  `ba0f3db2512013a4ecd8a3095c2536bc34889a58e6b3355ef0d9b664ab9d56fe`;
  no second SSH session or launch was performed.
- The current CI repairs change `conandata.yml` transport metadata, the
  post-primary-build Meson introspection launcher in `conanfile.py`, and one
  test-only patch limited to four `tests/api/` files.
  `reports/w3-current-input-rebind.json` binds 11/13 CI inputs byte-for-byte to
  the r20 semantic baseline. `conandata.yml` changes only the authority mirror
  from direct HTTP to direct HTTPS plus repository-required numeric patch
  labels; the downloaded 426972-byte source retains the official SHA-256.
  The report binds 0007 through exact full-post-image equivalence, together
  with the 13/13 production-method matrix, 586/586
  upstream suite, and 6/6 `tmpfile()` helper matrix. Relative to historical W3,
  23/23 installed
  runtime/package content files are byte-identical; only generated
  `conanmanifest.txt` changes with the RREV. The fresh consumer compiles and
  links, but its bytes are not claimed identical to the historical consumer.
  The immutable r36 26/26 terminal is rebound without a second device launch;
  the successor fail-closed matrix passed 12/12.
