# LevelDB 1.23 HarmonyOS PC notes

## Scope

- Upstream tag `1.23` resolves to commit
  `99b3c03b3284f5886f9ef9a4ef703d57373e61be`.
- The package installs the shared LevelDB C/C++ library and public headers.
- The `leveldbutil` executable and test-only static library are not packaged.

## Dependencies

The only required dependency is CMake `Threads`, which is a platform system
library. Upstream probes crc32c, Snappy, and tcmalloc automatically; all three
probes are explicitly disabled because they are optional and are not published
as dependencies for this adaptation.

The release archive omits Git submodule contents. The recipe therefore fetches
the exact upstream-pinned googletest commit `c27aceb...` and benchmark commit
`bf585a2...` from their official repositories with SHA256 verification.

## Test strategy

With `BUILD_SHARED_LIBS=ON`, upstream exposes only eight public-API tests. The
remaining 22 tests use internal symbols and are enabled only for a static
build. The recipe keeps the installed package shared and creates a second,
non-installed static CMake tree that compiles all 30 POSIX upstream tests.

On a native OHOS builder, CTest runs all 30 targets. During Windows-to-OHOS
cross compilation, `can_run` is false, so the build records compilation and
linking evidence without claiming that target binaries executed.

The consumer test links through `leveldb::leveldb`, creates a relative-path
database in its writable working directory, and verifies Put, Get, WriteBatch,
Delete, and cleanup behavior.

## Validation

The first configure failed because Windows-hosted Ninja cannot relink an OHOS
ELF to change its install RPATH. Setting `CMAKE_BUILD_WITH_INSTALL_RPATH=ON`
and `$ORIGIN` fixed the relink boundary while keeping the package relocatable.

The pre-fix HEAD `66ab1bff` rebuild in Buildbot #8993 (build raw log 53496)
later failed while configuring the bundled googletest because CMake 4 removed
compatibility with policy versions older than 3.5. Following E187, the recipe
passes `CMAKE_POLICY_VERSION_MINIMUM=3.5` to both the formal package build and
the separate static upstream-test build. Both trees need the setting because each
performs an independent CMake configure.

Upstream LevelDB and its pinned test dependencies use `-Werror`. Clang 15
reports `deprecated-copy` in the old googletest commit and
`unused-but-set-variable` in the old benchmark commit. Following E063, the
OHOS-only patch exempts only those two warning categories on the affected
test dependency targets; LevelDB and all other `-Werror` checks remain active.
The local Windows SDK also emits an unused `--gcc-toolchain` warning. That
host-only warning was handled in the untracked local toolchain wrapper and is
not part of the recipe or source patch.

The native HarmonyOS rebuild at HEAD `5fafcd93` reached target execution but
failed 11 of 30 tests because LevelDB defaulted its test databases to `/tmp`,
which is unavailable on the worker. Following E002, the recipe now creates a
clean writable directory inside the test build tree and exports it through
LevelDB's upstream `TEST_TMPDIR` interface while CTest runs. This preserves all
upstream tests and does not alter their assertions or source files.

The next native rebuild at HEAD `1590940e` was Buildbot #9247 (checkout raw
54976, build raw 54982). It compiled the full static upstream-test tree, then
failed before CTest because Conan 2.29.1 defines `apply()` on the `EnvVars`
object returned by `Environment.vars(self)`, not on `Environment` itself. The
recipe now uses `with test_env.vars(self).apply():` so `TEST_TMPDIR` is scoped
to the CTest process and the caller's environment is restored afterward.

Buildbot #9347 at HEAD `efad166cd` (checkout raw 55536, build raw 55539)
confirmed that the corrected context manager reached native CTest, but only
22/30 targets passed. The remaining tests use pinned Googletest
`testing::TempDir()`, whose POSIX implementation returns `/tmp/` directly and
therefore bypasses LevelDB's `TEST_TMPDIR` handling. The portability patch now
makes that pinned Googletest implementation honor `TEST_TMPDIR` when it is
set, including the required trailing slash, while preserving its upstream
`/tmp/` fallback when the variable is absent. No test source or assertion is
changed. A new current-HEAD native CI run must still prove all 30 targets.

The final forced `conan create` completed:

- 42/42 main shared-library build steps;
- 160/160 static upstream-test build steps;
- all 30 POSIX upstream test executables;
- one real consumer that compiles and links Put, Get, WriteBatch, Delete, and
  cleanup operations.

The resulting package contains 15 public headers, the license, and
`libleveldb.so.1.23.0` plus its two versioned names. It contains no static
archive, command-line tool, test dependency, or Windows path. The library is
an AArch64 ELF64 object with SONAME `libleveldb.so.1` and RUNPATH `$ORIGIN`.
Representative static test executables do not list `libleveldb.so` in NEEDED.

The Conan option contract was also generated with `shared=False` and
`fPIC=False`; the resulting toolchain set both `BUILD_SHARED_LIBS=OFF` and
`CMAKE_POSITION_INDEPENDENT_CODE=OFF`. Shared builds continue to force PIC.

Conan result: recipe revision `258688b37cc8e767fa81250f5ba057cc`, package
ID `01d92cf349a0dd98ff915f4bd99a04430171517f`, package revision
`37060d6638b1ef2186fb21a87a728d9c`.

Full stderr log:
`C:\Users\cxy\Documents\Codex\.tmp\leveldb-gtest-tmpdir-fix-20260719-v2.stderr.log`
(SHA256 `6F8310D44F2E251E2B610B884AF77C73AB9B2A66CB7EBA9C7BDE8E47DE8CC760`).

This Windows-to-OHOS rebuild verifies that the `TEST_TMPDIR` remediation keeps
all 30 upstream executables and the real consumer buildable. Inspection of
Conan 2.29.1 confirms that `Environment.vars(self)` returns the `EnvVars`
object that defines `apply()`. Cross-build execution remained skipped because
`can_run()` was false.

Buildbot #9388 later checked out HEAD `75daf10d107ce55f2dbfaa7565c5fcd86ce1d64d`
and its raw log proved CTest 30/30, the real `test_package`, L0/L1 pass, and
exit code 0. That CI result remains historical evidence for that exact HEAD.

On 2026-07-24, the same AArch64 outputs were independently deployed to a
HarmonyOS PC running HongMeng Kernel 1.12.0. Every ELF and the SONAME library
copy were signed in their final HMDFS paths. All 30 upstream test executables
and the shared-package consumer ran in isolated writable directories with
per-test `TEST_TMPDIR` values: 31/31 executable targets passed. The upload
payload SHA256 was
`7083f5a0c3ccef02088d47b6a01bcfc073ec7bde58cf35ca8b9c458f7e81c287`.
Signed SHA256 examples were:

- `test_leveldb`: `f26f08decda0e33ff06a1778c63b0d3e99b25bd735847086d0f53b2c011e4b87`;
- `libleveldb.so.1`: `9b813e7caaef1c1ca8120d8fd75a4e834aa1000de5647819bb17a3629d9caddd`;
- `c_test`: `c7a905cadfe23724a4c5cea20aae3967bfa4d59810e618ced7e99bc716c368e7`;
- `db_test`: `e2bc94c7069eda4e90f6efd8aa55724ee4e56e25d4ddde2b2aca926ac5236c86`;
- `env_posix_test`: `462aae5f64a763e18d05c9da3fa0f9a7db0d3ee88c5c2fa0bc4d0030cef43fa2`.

## Knowledge and adaptation path

This dependency PR uses **Path A + Path B**. Path B is justified by the
verified E218 draft (`knowledge/graph/draft/E218-draft-CX17.kv` and
`knowledge/graph/draft/E218-draft-CX17.md`), which
turns the LevelDB-specific shared/static test split into a reusable Conan/CMake
dual-build procedure with defined inputs, outputs, execution boundaries, and
package-audit rules. The CI remediation also reuses E002 for the writable test
directory and E187 for CMake 4 compatibility; it does not create a duplicate
knowledge entry.

LevelDB does not qualify for Path C: it uses public CMake/Clang tooling, has no
private OS API, assembly, closed binary, special scheduler, or large mandatory
dependency chain. Its upstream test set is bounded and compiled successfully.
