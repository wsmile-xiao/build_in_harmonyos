# crasm 1.11 HarmonyOS adaptation notes

## Status

- Branch: `feat/crasm-1.11-windrel`
- Issue: 待补。本轮已在项目文件、远端分支名和本地上下文中搜索 `crasm`，未找到明确 issue 编号。
- Current state: 真机单包 CI 已通过，待补 issue 编号后提交 PR。

## W0 Dependency Check

- Runtime/build dependencies: none beyond the C toolchain, libc and libm.
- Conan dependencies: none.
- Dependency split requirement: not applicable.

## Source and Build Analysis

- Source: Debian orig tarball mirroring upstream crasm 1.11.
- SHA256: `23983da187d5cd3e4e51d2fa4fe10a734660b5cb5c02e1bd01b62915137c6866`.
- Build system: plain Makefile.
- Main binary: `src/crasm`.
- Upstream tests: `make -C test test` assembles 11 sample 6800/6502/Z80 programs and diffs S-record outputs.
- OHOS adaptation point: upstream Makefiles set `SHELL=/bin/sh`; recipe passes `SHELL=sh` to avoid systems where `/bin/sh` is absent.

## Recipe Notes

- Build uses `tools.build:compiler_executables` to obtain the C compiler and passes it as `CC=...`.
- Build invokes `make -C src -j1 SHELL=sh` and, when executable tests can run, `make -C test -j1 SHELL=sh test`.
- The package installs `bin/crasm`, `share/man/man1/crasm.1`, and license files.
- On OHOS, the recipe attempts to self-sign the built/package executable if `/data/service/hnp/bin/binary-sign-tool` is available.
- `test_package` executes the packaged CLI against a small 6502 assembly fixture and compares normalized S-record output.

## Local Preflight Results

- Downloaded `crasm_1.11.orig.tar.gz` and verified SHA256 locally.
- Built upstream source on Windows with MinGW GCC: `mingw32-make -C src -j1 CC=gcc` succeeded.
- Ran upstream `make -C test test`; functional assembly ran, but Windows-host diff failed because generated S-record files used CRLF while reference files used LF. This is a host line-ending artifact; OHOS/Linux should not hit this exact diff.
- Local `conan create` was not run because `conan` is not installed in this Windows environment.

## OHOS Device CI Results

- Date: 2026-07-31 (Asia/Shanghai).
- Command: `CI_PACKAGES="archives/c/crasm/1.11" zsh ci/conan/build_and_test.sh archives/c/crasm/1.11`.
- Result: pass; `Total: 1`, `Success: 1`, `Failed: 0`.
- Upstream tests: pass; recipe ran `make -C test -j1 SHELL=sh test` and assembled all 11 upstream sample programs.
- Consumer smoke test: pass; `test_package/test_crasm.sh` assembled a tiny 6502 program and compared normalized S-record output.
- L0: pass, including version collision check and software-level `commands.json` check.
- L1: pass; test_package execution and destructive negative test confirmed the smoke test depends on packaged `crasm`.
- L2: non-blocking skip/warn because `crasm --version/--help` is unsupported by upstream CLI; bare `crasm` prints syntax/version and the functional smoke test passed.
- L4: pass; no patches.
- L5: pass; `bin/` contains packaged executable.
- Device log: `/storage/Users/currentUser/validation/build_in_harmonyos/.ci_logs/conan_build_crasm_1.11.log`.

## PR/CI Verification Commands

```sh
cd /path/to/build_in_harmonyos
conan create archives/c/crasm/1.11 --user=ohpcd --channel=stable \
  -pr:h=$HOME/.conan2/profiles/ohos \
  -pr:b=$HOME/.conan2/profiles/ohos \
  --build=missing

CI_PACKAGES="archives/c/crasm/1.11" zsh ci/conan/build_and_test.sh

# If using the shadow CI runner:
/path/to/run-ohos-shadow-ci.sh archives/c/crasm/1.11
```

## Blocking Points

- Issue 编号待补。
- PR CI still needs to run after pushing/opening the PR.
