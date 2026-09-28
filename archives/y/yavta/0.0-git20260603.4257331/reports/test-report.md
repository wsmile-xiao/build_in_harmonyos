# Yavta 0.0-git20260603.4257331 test report

> Test date: 2026-09-27
> Test environment: Windows host, OpenHarmony SDK 26.0.0 / clang 15.0.4 / Meson 1.11.1 / Ninja 1.13.2, HarmonyOS PC x86_64 emulator (`hdc`)
> Test type: Conan package builds, HarmonyOS emulator execution, repository CI checks

## 1. Test summary

| Check | Result | Details |
|---|---|---|
| Upstream test inventory | PASS | The source has no `tests/` or `test/` directory, and no Meson `test()` registration. `meson test --list` reported `No tests defined.` (Meson returns 1 when no tests are registered). |
| Conan x86_64 package | PASS | `conan create` compiled and packaged the OHOS x86_64 ELF. |
| Conan AArch64 package | PASS | `conan create` compiled and packaged the OHOS armv8 ELF. |
| ELF architecture | PASS | `llvm-readelf` identified ELF64 x86-64 and ELF64 AArch64 respectively. |
| HarmonyOS emulator test | PARTIAL | The CLI assertions passed and the consumer script returned 0. V4L2 format enumeration was skipped because the emulator did not expose an accessible video device. |
| Repository test suite | PARTIAL | `tests/run_all.py` completed 11 of 12 test files. `test_v1220.py` could not start its temporary Git repository because its hard-coded `/data/service/hnp/git.org/git_2.45.2/bin/git` path is unavailable on this Windows host. |
| Local CI quality gates against `upstream/main` | PASS | The 11-file PR diff passed `junk_check.sh` (JC1–JC6), `knowledge_check.sh` (KC1–KC5), and `git diff --check`. JC6 confirmed exactly one software package. |
| Full local CI pipeline | NOT RUN | This Windows host has no `zsh` or CI worker HNP environment. A prior local attempt used `origin/main` and stopped at the junk-file gate because that base differs from this branch's required `upstream/main`; it is not counted as a current CI result. |
| Upstream PR CI | PENDING | The pushed change is in PR #13240. The GitCode CLI has no configured access token, and the desktop browser inventory was unavailable, so the upstream `/rebuild` trigger and resulting CI status could not be verified here. |

## 2. Conan and device execution

Both target builds used the installed HarmonyOS SDK and completed Meson configure, compile, install, and package creation. On this Windows host, Conan's Meson helper generated `--prefix=C:/` for cross builds, which Meson rejects for an OHOS target. For these local cross-build checks only, a temporary process-level shim set the target prefix to `/`; no such workaround was added to the package recipe. A native OHOS worker uses `/` directly.

Conan launched the `test_package` graph for both cross builds and correctly skipped executing the target binary on Windows (`can_run` is false). The same `test_package/test.sh` was then run on the HarmonyOS emulator using `/system/bin/sh`:

- `PASS: usage line`
- `PASS: --help option`
- `SKIP: no accessible V4L2 video device`
- `HDC_TEST_SCRIPT_EXIT=0`

A direct `hdc shell /data/local/tmp/yavta --help` invocation also returned 0. The emulator did not permit inspection of `/dev` and returned `Permission denied` when Yavta attempted to open `/dev/video0`; `/dev/null` opened, but its V4L2 capability query was also denied. Therefore the emulator could not verify a real camera driver's format enumeration, capture, or streaming operations.

## 3. Upstream inventory evidence

The pinned source snapshot matches all seven files in upstream commit `42573311466dbeab630d084bc2d5afe88154690b` byte-for-byte. It has no `tests/` or `test/` directory and no test-like source files. After setup, `meson test --list` returned `No tests defined.` Therefore the upstream suite contains zero runnable tests; the consumer checks cover the installed CLI's help interface and enumerate V4L2 formats when an accessible video node is available.

## 4. Local CI status against upstream/main

The full `ci/conan/build_and_test.sh` pipeline could not be run on this Windows host because `zsh` and the CI worker's `/data/service/hnp` environment are unavailable. The local quality gates that can run here were given the exact PR file diff generated from `upstream/main...HEAD`:

- `junk_check.sh`: PASS, prdiff mode, 11 changed files; JC1–JC6 passed and one software package was detected.
- `knowledge_check.sh`: PASS, all five knowledge graph checks passed.
- `git diff --check upstream/main...HEAD`: PASS.

An earlier local pipeline attempt compared against `origin/main` rather than `upstream/main`; it stopped at the junk-file gate after that unrelated diff included other packages. This is recorded as a historical environment/base mismatch, not as the result of the current upstream-based quality gate run.

## 5. PR CI follow-up

PR build 62835 passed the package quality and junk-file gates and downloaded the pinned source, then stopped during Meson configuration because the worker could not find llvm-ar on PATH. The Conan recipe now resolves the archiver from the configured compiler directory or the OHOS SDK and pins its absolute path in MesonToolchain.

Forced Conan source builds with the local OHOS SDK passed for x86_64 and AArch64. On Windows, Conan correctly skipped executing the target binaries in `test_package`; the HarmonyOS x86_64 emulator ran both CLI help assertions, but its device policy prevented V4L2 driver access. The test now enumerates formats on an accessible `/dev/video*` node when one is available and reports a skip when none can be accessed. The upstream `/rebuild` trigger and resulting remote CI status are pending because no GitCode API token or browser session was available on this host.
