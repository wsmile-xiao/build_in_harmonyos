# liblbfgs 1.1 HarmonyOS adaptation notes

## Scope

- Library: liblbfgs
- Version: 1.1
- Worktree: `D:\harmonyos\worktrees\liblbfgs`
- Package directory: `archives/l/liblbfgs/1.1`
- Issue: ignored per user instruction for this round.

## W0 dependency check

- Upstream source exists at `https://www.chokkan.org/software/dist/liblbfgs-1.1.tar.gz`.
- Source SHA256: `5b71d193a5f44ce958f123f6ae58be4355547cbf722a50d2aaf06eda1c69de23`.
- The true 1.1 tarball extracts directly into `include/`, `src/`, and `COPYING`; it has no top-level source directory.
- The 1.1 source tree has no configure script, Makefile, CMakeLists, or other build system. The Conan recipe generates a minimal CMake wrapper for the raw C source.
- No Conan package dependencies are required. Runtime link dependency is the system math library `m` on Linux/OHOS.
- `conan list 'liblbfgs/*' -r=ohpcd` found no recipes on the configured OHPCD remote. Direct `conan download liblbfgs/1.1 -r=ohpcd --only-recipe` returned the remote-side error `error:system acceleration policy not enabled`, so the collision check is treated as unresolved by direct download but clear by list query.

## Source and build analysis

- Public header: `include/lbfgs.h`.
- Library source: `src/lbfgs.c`.
- Upstream sample: `src/main.c`.
- liblbfgs 1.1 API differs from newer liblbfgs releases:
  - `lbfgs()` has no `ptr_fx` output argument.
  - `lbfgs_malloc()` and `lbfgs_free()` are not present.
- A portability patch adds `#include <string.h>` to `src/lbfgs.c` because the source uses `memcpy()`.
- The same patch updates upstream sample `main()` from `char *argv` to `char **argv`; OHOS clang treats the old argument-array type as an error.
- The upstream 1.1 sample is compiled but not executed. It calls `evaluate(NULL, x, NULL, N, 0)` after optimization, which dereferences a NULL gradient buffer.

## Conan/test_package plan

- Recipe uses `get(..., strip_root=False)` because the archive has no root directory.
- Recipe generates a CMake project that builds:
  - `lbfgs` library from `src/lbfgs.c`.
  - `liblbfgs_sample` from upstream `src/main.c` as a compile-only target.
  - `test_liblbfgs_build`, a build-time API/convergence smoke test.
- `test_package` builds a C consumer using the 1.1 API and checks:
  - `lbfgs_parameter_init()` defaults.
  - callback invocation.
  - optimizer return code.
  - convergence to `(1.0, -2.0)` on a convex quadratic.
  - final objective tolerance.

## Local validation performed

- `conan inspect` with isolated local Conan home.
- `conan export` with isolated local Conan home.
- `conan source` against the true 1.1 archive using a temporary recipe copy, including patch application.
- Linux Conan graph resolution with full host/build settings.
- `conan create` Linux attempt reached export, source, patch, and generate, then failed at `CMake.configure()` because this Windows host has no usable Unix/CMake/compiler runner for that Linux build profile.
- Static source checks for 1.1 API usage and generated CMake wrapper contents.
- YAML parsing for `conandata.yml`, `manifest.yaml`, and `test_package/MANIFEST.yml`.
- Python syntax checks for recipe files.
- `git diff --check` on `archives/l/liblbfgs/1.1`.

## Local blockers

- No local C compiler, CMake, Ninja, Make, or zsh was found in PATH, so a native compile/run could not be completed on this machine.
- `zsh` is not available locally, so `ci/conan/build_and_test.sh` could not be executed here.
- A community Conan 2.29.1 install from the OHPCD PyPI mirror still rejected `OHOS` as an invalid setting on this Windows host; OHOS graph/build validation should be run on the patched CI/device runner.

## Next OHOS/shadow CI commands

```sh
cd /path/to/build_in_harmonyos
CI_PACKAGES="archives/l/liblbfgs/1.1" zsh ci/conan/build_and_test.sh
```

For first real-device verification, use the documented isolated runner/TMPDIR flow and keep this as a single-package job.

## Shadow CI on real device

- Device: `currentUser@10.62.220.52:2222`.
- Remote isolated worktree: `/storage/Users/currentUser/ohpc-ci-shadow/worktrees/liblbfgs-1.1-20260825T122828Z-65390`.
- Remote temporary commit for shadow runner: `fb1712a8acdb37a80eefbf848be7f85d0a8b97fa feat(liblbfgs): add 1.1 recipe`.
- First shadow CI run: `/storage/Users/currentUser/ohos-test-runs/codex-liblbfgs-shadow-ci-1.1-20260825-203352-6915`, exit 1 at L0 with `commands_json_r38` because the generated CMake install block included `RUNTIME DESTINATION bin`.
- Fix applied: removed `RUNTIME DESTINATION bin` from the generated CMake wrapper. `detect_bindirs.py` now returns `0`, and there is no `RUNTIME DESTINATION bin`/`dst="bin"` match in the recipe.
- Second rerun: `/storage/Users/currentUser/ohos-test-runs/codex-liblbfgs-shadow-ci-1.1-r3-20260825-205652-21803`, reached L1 and failed during sample compilation because OHOS clang rejects `int main(int argc, char *argv)`. Patch updated to use `char **argv`.
- Passing rerun: `/storage/Users/currentUser/ohos-test-runs/codex-liblbfgs-shadow-ci-1.1-r4-20260825-220817-65005`.
- Shadow run dir: `/storage/Users/currentUser/ohpc-ci-shadow/runs/20260825T141501Z-fb1712a8ac-3539`.
- Result: exit 0; `G0_RESULT=pass`, `L0_RESULT=pass`, `L1_RESULT=pass`, `L2_RESULT=skip: no bin/ dir`, `L4_RESULT=pass`, `L5_RESULT=pass`.
- Package revision on device: `6ada7caf82c69cae04905deec79d7885`.
- Test evidence: `liblbfgs/1.1 smoke test passed: ret=0 fx=0 progress=2`.
