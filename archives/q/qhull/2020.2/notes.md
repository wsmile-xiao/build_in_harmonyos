# Qhull 2020.2 HarmonyOS PC notes

## Scope

- Upstream tag `2020.2` and `v8.0.2` resolve to commit
  `613debeaea72ee66626dace9ba1a2eff11b5d37d`.
- The package exposes the reentrant shared C library `qhull_r`.
- Static libraries, the C++ wrapper, documentation, and command-line tools are
  excluded from the package. Upstream tools and test executables are still
  cross-compiled as build validation.

## Dependencies

Qhull has no third-party Conan dependencies. The upstream CMake build links
`libqhull_r` to the platform math library `m`.

## Platform adaptation

Upstream assigns the relative string `lib` as the installed RUNPATH and asks
CMake to relink during installation. The patch uses `$ORIGIN` and links with
the final install RUNPATH from the initial build, which is suitable for the
Windows-to-OHOS cross-build and keeps the packaged shared library relocatable.

Windows cross-built test executables otherwise retain host cache paths while
linking `libqhull_r.so`. Following the existing
`openharmony-conan-cmake-upstream-tests-cross-runpath` rule, OHOS builds create
non-installed static targets for the upstream CTest executables. The patch
therefore keeps all test applications in the default build while excluding
them from the OHOS install target list. The final Conan package removes every
static archive and remains shared-only.

## Verification boundary

The full Conan build, upstream test-target compilation, consumer compilation,
ELF architecture, and RUNPATH are cross-build evidence. Target runtime was
verified separately on a HarmonyOS PC: eleven upstream CTest scenarios and the
Conan consumer all executed successfully.

## Validation

The first `conan create` reached CMake generation and failed because the six
Qhull command-line applications were still install targets. Ninja would have
needed to relink their OHOS ELF files on the Windows host. The patch now keeps
those applications in the default build for upstream test coverage but omits
them from the OHOS install target list.

The pre-fix HEAD `4f8164d2` rebuild in Buildbot #8984 (build raw log 53439)
later failed at the top-level CMake configure because CMake 4 removed
compatibility with policy versions older than 3.5. Following existing
knowledge E187, the recipe
passes `CMAKE_POLICY_VERSION_MINIMUM=3.5` through `CMakeToolchain` without
patching upstream version declarations. Runtime gating now uses Conan
`can_run()` consistently for both upstream tests and the consumer.

The historical Buildbot 9226 run (checkout raw 54849, build raw 54854) checked
out the then-current recipe and exposed a Conan CMake helper API mismatch:
`cmake.test(cli_args=...)` forwards those arguments to
`cmake --build --target test`, where CMake 4 rejects
`--output-on-failure`. The recipe now uses `cmake.ctest(cli_args=...)`, whose
documented contract passes the arguments to CTest itself.

The final clean `conan create` completed 104/104 upstream build steps and
linked a real consumer that calls `qh_new_qhull`, checks the square hull's
vertex/facet counts, and frees all Qhull allocations. The resulting package:

- contains only 11 `libqhull_r` headers, `libqhull_r.so` and its versioned
  names, the license, and Conan metadata;
- contains no static archive, command-line tool, deprecated non-reentrant
  headers, or C++ wrapper headers;
- provides an AArch64 ELF64 shared object with SONAME `libqhull_r.so.8.0` and
  RUNPATH `$ORIGIN`;
- has zero embedded Windows build paths;
- produced 11 AArch64 upstream executables and one AArch64 consumer.

Conan result: recipe revision `4ed15b365f9cd77d6a5c1dc1edcafc6f`, package
ID `01d92cf349a0dd98ff915f4bd99a04430171517f`, package revision
`213791c4bfe43c3b400e22406e5da703`.

Current-diff build log:
`C:\Users\cxy\Documents\Codex\.tmp\qhull-ctest-api-fix-20260719-v2.stderr.log`
(SHA256 `6101BD2DE4AA2E1D6515B9B2FEF6A7E52058019575AEE7DB6E6D215C5876C514`).

The twelve target tests were transferred to
`/storage/Users/currentUser/codex-tests/pr-3007` with per-file SHA256
verification, then signed in place at their final HMDFS paths. All eleven
upstream CTest commands and the Conan consumer returned zero (12/12). The
consumer printed `Qhull consumer test passed`; its unsigned and signed SHA256
values were
`1558f4ba8c8e7ca788bce2ca9d690968848d08effd0dc2868a788f6a4c5542db` and
`7cb967d77807d0e3f0388511e3360c22a5879b34ae419097a8749c26fc80ea65`.

## Knowledge decision

This adaptation reuses the existing
`openharmony-conan-cmake-upstream-tests-cross-runpath` rule for non-installed
static cross-test targets and E187 for CMake 4 compatibility. It does not
introduce a new general error pattern, so no new formal knowledge entry or path
B claim is added. Qhull itself uses a public CMake/Clang toolchain, has no
third-party Conan dependency, and has a bounded C API/test surface; the
downstream graph-tool difficulty does not make this dependency a path C
library.
