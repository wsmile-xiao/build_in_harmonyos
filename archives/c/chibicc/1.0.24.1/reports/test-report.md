# chibicc 1.0.24.1 preflight test report

## Scope

This report covers local preflight plus the OHOS shadow CI run completed on `2026-08-06`.

## Checks Performed

| Check | Result | Notes |
| --- | --- | --- |
| Worktree isolation | PASS | Created `D:\harmonyos\worktrees\chibicc` on `feat/chibicc-1.0.24.1-1894`; main worktree was not switched. |
| Source discovery | PASS | `rui314/chibicc` has no `v1.0.24.1` tag; selected Debian primary sourcefiles authority mirror for `chibicc_1.0.24.1.orig.tar.gz`. |
| Source integrity | PASS | SHA256 verified as `cbcdaccce25508566b77f26e2ffab41a379e05b6a0be73a5b6806796db62fecc`. |
| Build-system analysis | PASS | Selected upstream Makefile; rejected bundled CMakeLists.txt because it requires Boost and does not match the C-only upstream build. |
| Dependency analysis | PASS | Identified `openssl/3.5.6.1` as the only Conan dependency due to upstream `-lcrypto` link flag. |
| Python syntax check | PASS | Parsed `conanfile.py` and `test_package/conanfile.py` with bundled Python AST parser. |
| Conan verification | BLOCKED | `scripts/ohc-run.py conan-verify chibicc 1.0.24.1` stopped at `Conan CLI 不可用`. |
| OHOS shadow CI r1 | FAIL | Isolated `CONAN_HOME` did not contain `ohpcd`; `openssl/3.5.6.1` could not be resolved. |
| OHOS shadow CI r2 | FAIL | `openssl/3.5.6.1` downloaded from `ohpcd`; build then failed because `make` is not available on the runner. Recipe updated to direct compiler invocation. |
| OHOS shadow CI r3 | FAIL | After device recovery, chibicc built, packaged, and signed successfully; `test_package` failed because shell here-doc creation used read-only `/tmp`. Test script updated to use package-local `TMPDIR` and `printf`. |
| OHOS shadow CI r4 | FAIL | chibicc built, packaged, and signed successfully; `test_package` generated assembly but expected a direct `call add`. Generated output uses `call *%r10`, so the smoke assertion now checks for a call instruction without binding to direct-call spelling. |
| OHOS shadow CI r5 | PASS | Run directory `/storage/Users/currentUser/ohos-test-runs/currentUser-chibicc-chibicc-1.0.24.1-1894-conan-r5-20260806-225629-3944`; `conan create` passed, `test_package` executed, `chibicc --version` passed, summary `Success: 1`, `Failed: 0`. |
| OHOS shadow CI r6 | PASS | Run directory `/storage/Users/currentUser/ohos-test-runs/currentUser-chibicc-chibicc-1.0.24.1-1894-conan-r6-r39-source-20260806-235436-7837`; sources downloaded from official GitHub tag URL, `conan create` passed, `test_package` executed, summary `Success: 1`, `Failed: 0`. |
| OHOS shadow CI r7 | PASS | Run directory `/storage/Users/currentUser/ohos-test-runs/currentUser-chibicc-chibicc-1.0.24.1-1894-conan-r7-r39-authority-mirror-20260807-003457-40949`; sources downloaded from Launchpad Debian primary sourcefiles authority mirror, `conan create` passed, `test_package` executed, summary `Success: 1`, `Failed: 0`. |
| Local conan create | NOT RUN | `conan` is not installed in the Windows PATH. |

## Consumer Smoke Test Design

`test_package/test_chibicc.sh` runs the packaged `chibicc`, compiles a tiny C source with `-S`, and asserts:

- `bin/chibicc` is executable.
- `hello.s` is created and non-empty.
- Generated assembly contains `main:`.
- Generated assembly contains `add:`.
- Generated assembly contains a `call` instruction.

The test stops at assembly generation because chibicc emits x86-64 output, while the OHOS target device is expected to be armv8.

## Last Shadow CI Command

```sh
JOB=/storage/Users/currentUser/ohos-users/currentUser/chibicc-1.0.24.1-1894-20260806-184059
. "$JOB/env.sh"
CONAN_HOME="$JOB/conan-home" sh "$HOME/bin/ohos-test-runner.sh" \
  --user currentUser \
  --lib chibicc \
  --task chibicc-1.0.24.1-1894-conan-r7-r39-authority-mirror \
  --mode heavy \
  --try-lock \
  --workdir "$CI_REPO_ROOT" \
  -- zsh ci/conan/build_and_test.sh "$CI_PACKAGES"
```
