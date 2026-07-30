# Boost 1.90.0.1 Morpheus dependency notes

## Scope

This package is the Morpheus-specific repair suffix for upstream Boost 1.90.0.
The existing `boost/1.90.0` recipe is header-only, while Morpheus CLI needs
linkable Boost components:

- `Boost::program_options`
- `Boost::filesystem`
- `Boost::system`

The recipe therefore uses the official Boost CMake release asset and builds
only the minimal dependency closure: `atomic`, `container`, `filesystem`,
`program_options`, and `system`. It intentionally does not copy the larger Redex/FastNetMon
component set from other open PRs.

## Issue/PR split

- Morpheus task: Issue #1298
- Dependency issue: #1480
- Branch: `feat/boost-1.90.0.1-morpheus`
- File scope: `archives/b/boost/1.90.0.1/**`

The issue text explicitly states that this is the Morpheus-required version and
that existing `boost/1.90.0` header-only artifacts are a different version
contract.

## Validation plan

1. Rerun Windows/MinGW Conan simulation for `boost/1.90.0.1` once the source
   archive can be fetched reliably.
2. Run OHOS single-package validation for `boost/1.90.0.1`.
3. After publication, run Morpheus with this package in the host dependency
   graph.

The consumer test verifies that CMake can resolve and link
`Boost::program_options`, `Boost::filesystem`, and `Boost::system`.

## Local status

Static checks passed on 2026-07-26:

- `python -m py_compile conanfile.py test_package/conanfile.py`
- `conan inspect`
- `conan export`
- `git diff --check`

Windows/MinGW `conan create` was started with workspace-local `CONAN_HOME` and
`TEMP/TMP`, but did not reach configure/build. The GitHub
`boost-1.90.0-cmake.tar.xz` source archive is 101.6MB; the local run timed out
after 20 minutes at 31,129,600 bytes downloaded. Next execution should either
reuse a completed source cache or run on the OHOS worker/network path.

## OHOS status

2026-07-28 r7 on the isolated OHOS job built and installed the four shared
libraries `libboost_atomic.so`, `libboost_container.so`,
`libboost_filesystem.so`, and `libboost_program_options.so`, then signed them
successfully. The generated consumer executable was also built and signed.

The complete OHOS wrapper run passed:

- run_dir: `/storage/Users/currentUser/ohos-test-runs/codex-a-boost-boost-1.90.0.1-20260728-r1-conan-r7-l5nopipe-20260728-150149-22007`
- package revision: `boost/1.90.0.1#0e67c4d18533fbb41099c63f30d3c12f:01d92cf349a0dd98ff915f4bd99a04430171517f#2b240dcba2008dc970dc4599973c4e74`
- L0=pass, L1=pass, L2=skip(no bin/ dir), L4=pass, L5=pass
- Build Summary: Total 1, Success 1, Failed 0

Earlier r5/r6 wrapper runs exited 141 after `conan create` had already printed
`[ok] boost/1.90.0.1 -- conan create passed`. The cause was in CI L5/R26
post-processing, where `find | head` and `ls | xargs` pipelines can trip zsh
`pipefail`/SIGPIPE while scanning large package/system library trees. The CI
wrapper now uses `find -print -quit` and direct zsh glob iteration instead of
those pipelines.

Manual reruns of the same signed `test_boost_morpheus_components` executable
returned 0 both with and without `conanrun`; an independent OHOS runner
`conan test` also regenerated, built, signed, and executed the test package with
exit code 0. Dynamic inspection confirmed
`libboost_program_options.so` has `NEEDED libboost_container.so`, so the Conan
component metadata now exposes `Boost::container` and makes
`Boost::program_options` require it.

## Upstream component tests

The full Boost test suite is large and Boost.Build based, so this PR validates
the Morpheus-relevant official component quick tests from the release source:

- `libs/system/test/quick.cpp`
- `libs/filesystem/test/quick.cpp`
- `libs/program_options/test/quick.cpp`

These three official tests were cross-compiled against the r7 Conan package,
signed, and executed on the OHOS device. Run directory:
`/storage/Users/currentUser/ohos-test-runs/codex-a-boost-boost-1.90.0.1-20260728-r1-upstream-quick-r1-20260728-150919-25874`.
Result: 3/3 passed (100.00%).
