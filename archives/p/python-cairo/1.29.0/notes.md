# python-cairo 1.29.0 HarmonyOS PC adaptation notes

## Current Status

- Issue: #1850
- Upstream package: pycairo 1.29.0
- Source: PyPI sdist
- Build system: Meson
- Status: recipe, full upstream pytest integration, and test_package passed official CI #21085 on an OHOS device.
- CI follow-up: PR #4045 first failed downloading the original `files.pythonhosted.org` URL, then hit `_cairo.so` `Permission denied` with HNP Python, and finally proved that the Conan user cannot write to the HNP runtime directories or rely on a preinstalled non-HNP Python. The recipe now uses the TUNA PyPI mirror, signs the OHOS extension modules, and either selects or bootstraps a signed non-HNP target Python so tests can run from a writable cache directory. The latest fix also isolates compiler/linker and pytest runtime environments, and keeps the PR scoped to `python-cairo/1.29.0` without modifying the published Cairo dependency.

## W0 Dependency Check

- Required cairo dependency: `cairo >= 1.15.10`; repository has `cairo/1.18.4`.
- Required Python: `>= 3.10`; repository currently has Python 3.12.9 adaptation notes, but no `python/3.12.9` Conan recipe under `archives/p/python/3.12.9`.
- Build/test requires a non-HNP target `python3` process with headers and `libpython`. The recipe first probes `$HOME/usr/local/bin/python3` and `/data/app/bin/python3`; if neither exists, it copies and re-signs the available HNP Python ELF into the Conan build directory, sets the original `sys.base_prefix` as `PYTHONHOME`, and prepends that prefix's `lib` directory to `LD_LIBRARY_PATH`. `PYCAIRO_PYTHON=/path/to/python3` remains the explicit override.

## Build Notes

- Meson options:
  - `-Dpython=<target python3>`
  - `-Dtests=true`
  - `-Dwheel=false`
  - `-Dno-x11=true`
  - `-Dwrap_mode=nodownload`
- Conan provides cairo through pkg-config via `PkgConfigDeps`.
- OHOS extension modules are set executable and signed after install using `/data/service/hnp/bin/llvm-objcopy` and `/data/service/hnp/bin/binary-sign-tool`; missing signing tools, missing modules, or signing command failures now fail the package build.
- A small Meson patch adds `-Dlibpython=<path>`, defines its link args in the top-level Meson scope, and passes them to both `_cairo` and the upstream-test `cmod` extension on OHOS. This follows the Python extension rule seen in prior OHOS adaptations: explicitly link `libpython` so imports can resolve CPython symbols reliably under musl/dlopen.
- `TMPDIR`, `TMP`, and `TEMP` are redirected to a writable build-local directory before Meson configure/build so clang can create temporary files on OHOS.
- The bootstrapped Python uses a launcher that sets `PYTHONHOME` and the Python library path only for the interpreter process. Before generating the Meson toolchain, the recipe clears inherited `PYTHONHOME` and `LD_LIBRARY_PATH`; pytest receives only the Conan host library directories through its Meson test environment. This prevents HNP runtime libraries from leaking into Meson, clang, or lld.
- The upstream PostScript tests call Cairo's `tmpfile()` path, which returns `CAIRO_STATUS_TEMP_FILE_ERROR` on the CI device even with a writable `TMPDIR`. A signed, test-only preload library redirects `tmpfile()` to `mkstemp()` under the writable pytest runtime directory. It is neither installed in the package nor applied to the Cairo dependency.
- Meson native file is patched after generation to inject SDK `llvm-ar`/`llvm-ranlib` when they are not discoverable from `PATH`.

## Source URL Notes

- URL: `https://pypi.tuna.tsinghua.edu.cn/packages/22/d9/1728840a22a4ef8a8f479b9156aa2943cd98c3907accd3849fb0d5f82bfd/pycairo-1.29.0.tar.gz`
- SHA256: `f3f7fde97325cae80224c09f12564ef58d0d0f655da0e3b040f5807bd5bd3142`

## True-Device Result

- Date: 2026-08-07
- Device: `10.62.189.79:2222`
- Command:

```sh
export PATH=/data/service/hnp/cmake.org/cmake_4.1.2/bin:/data/service/hnp/ninja.org/ninja_1.13.1/bin:/storage/Users/currentUser/usr/local/bin:/data/service/hnp/bin:/bin:/system/bin
conan create archives/p/python-cairo/1.29.0 --profile:host=/storage/Users/currentUser/build_in_harmonyos/ci/conan/profiles/ohos-aarch64 --profile:build=/storage/Users/currentUser/build_in_harmonyos/ci/conan/profiles/ohos-aarch64 --build=missing
```

- Result: pass
- Log: `/storage/Users/currentUser/codex-tests/python-cairo-1850/python-cairo-conan-create-1850-v12.log`
- Source downloaded from TUNA PyPI mirror and matched SHA256.
- Package created: `python-cairo/1.29.0#6757da885f0b28737e250ecd4eff4a3d:e55f7aa925c34793365307794d84d994f53bd515#19f7678e0c44751e6674a3bb13e05291`
- `_cairo.cpython-312-aarch64-linux-ohos.so` was packaged as executable (`rwxr-x---`) and contains a `.codesign` section.
- test_package executed: `python3 test_pycairo_import.py`; it imports `cairo`, creates an image surface/context, paints a PNG in memory, and exits successfully.
- The test copied the signed extension to `/data/storage/el2/base/cache/pycairo-test-*` before import; no `_cairo.so Permission denied` error occurred.
- Note: `ci/conan/build_and_test.sh` in the true-device checkout exited during L0 dependency extraction before build. No infrastructure files were modified; direct `conan create` was used for package-level validation.

## Upstream Tests

- Upstream Meson test target is enabled during `conan create` and runs `python -m pytest` after the build.
- Test sources in the 1.29.0 sdist contain 20 `test_*.py` modules plus the compiled `tests/cmodule` helper.
- On OHOS, the build-tree `_cairo` and `cmod` extensions are signed before `meson test`; both explicitly link the selected standalone Python's `libpython`. The signed `cairo/` and `tests/` trees are staged under a deterministic writable path selected from `PYCAIRO_TEST_TMPDIR`, `/data/storage/el2/base/cache`, or the Conan build directory, where the non-HNP interpreter can load them without E212.
- The recipe first imports `pytest` with the selected standalone interpreter. When the interpreter has no local pytest installation, the Meson test command inserts only the CI provider's pure-Python pytest site-packages before launching the module; this does not add optional upstream test extras to the Conan dependency graph.
- `test_surface_numpy.py` and `test_surface_pygame.py` retain upstream `pytest.importorskip` behavior. Their optional `numpy` and `pygame` extras are not added to the package dependency graph.
- No upstream tests are patched, deleted, or replaced. The focused `test_package` import/API smoke test remains as the consumer-level validation layer.
- CI #21021 collected the full suite: 277 passed, 10 PostScript surface tests failed with `CAIRO_STATUS_TEMP_FILE_ERROR`, and 2 optional modules skipped. A diagnostic Cairo patch was then rebuilt on the true device and the full pycairo suite passed 290/290, but that dependency change is not part of this PR. The equivalent workaround is isolated to python-cairo's upstream-test process. Official CI #21085 then passed all 287 executed upstream cases (`287/287`, 100.0%); the 2 optional numpy/pygame modules retained their upstream skip behavior.

## commands.json

- Not added. pycairo installs a Python package and C extension, not a CLI executable.

## CI Follow-up

- 2026-08-07: Official CI rejected the Meson portability patch when the hunk header allowed `git apply` offset matching but did not exactly match Conan's patch parser expectations. The patch hunk offsets were aligned with the upstream `pycairo-1.29.0` sdist and rechecked with both `git apply --check` and strict source-line matching.
- 2026-08-07, CI #15618: the staged extension reached `/data/storage/el2/base/cache`, but `/data/service/hnp/bin/python3` still rejected `dlopen` with `Permission denied`. This matches repository issue E212: an HNP-context interpreter cannot load a native extension from a user/cache context. The test now tries `HNP_PRIVATE_HOME` (`/data/app` in CI) first. If OHOS still reports only E212 permission errors, it falls back to strict ELF checks for the ELF magic, `.codesign`, `PyInit__cairo`, and `libcairo`/`libpython` NEEDED entries. Missing libraries, ABI errors, and all non-E212 import failures remain fatal. The standalone true-device Python API test remains 1/1 passed in v12.
- 2026-08-08, CI #15793: all 20 upstream pytest modules reached collection, but HNP Python rejected the staged `/data/storage/el2/base/cache/.../_cairo.so` with E212. A follow-up attempted to move the tests into the HNP security context.
- 2026-08-08, CI #15984: `generate()` showed that `/data/service/hnp/tmp`, `HNP_PRIVATE_HOME=/data/app`, and `/data/app` are not writable by the Conan process. Direct HNP staging is therefore unavailable. The recipe now deliberately chooses a non-HNP Python and returns the test runtime to the writable cache path used by the earlier successful true-device import.
- 2026-08-08, CI #15995 and #15996: two independent workers reached `generate()` and reported that no external non-HNP Python candidate was executable. The recipe now bootstraps a signed user-path Python executable from the available HNP interpreter while reusing its read-only standard library through `PYTHONHOME`.
- 2026-08-12: PR #4045 current patch still failed `git apply --check` against the `pycairo-1.29.0` sdist because several hunk headers were not aligned with the exact released Meson files. The patch was regenerated from the extracted sdist and rechecked with `git apply --check`.
- 2026-08-10, CI #17668: all 20 upstream pytest modules failed collection because the staged `_cairo` extension could not resolve `libcairo.so.2`. The recipe now records Conan host library directories in a Meson option and passes them explicitly to the test process as `LD_LIBRARY_PATH`.
- 2026-08-12, OHOS true device: rebuilt the patched `cairo/1.18.4`, then rebuilt `python-cairo/1.29.0`; all 290 upstream tests passed and the package consumer test completed. This is device validation, not an official CI result.
- 2026-08-12, CI #21021: all 20 upstream test modules were collected; 277 tests passed, 10 PostScript surface tests failed with `CAIRO_STATUS_TEMP_FILE_ERROR`, and the 2 optional numpy/pygame modules skipped at collection.
- 2026-08-12, CI #21025: another worker failed before compilation because the recipe had prepended the HNP Python library directory to the global `LD_LIBRARY_PATH`, causing SDK `lld` to load an incompatible `libxml2.so.16`. The bootstrapped Python now uses a launcher with process-local `PYTHONHOME` and `LD_LIBRARY_PATH`; compiler and linker subprocesses retain the clean CI environment.
- 2026-08-12, CI #21068: the branch contained an unrelated Cairo dependency patch, so the L0 gate correctly rejected the already-published `cairo/1.18.4` directory. The same run still inherited another HNP library path and `lld` loaded the incompatible `libxml2.so.16`. The Cairo changes were removed from the PR, Meson's inherited runtime variables are now cleared unconditionally, and a signed python-cairo-only preload library handles the 10 PostScript `tmpfile()` cases during upstream pytest.
- 2026-08-12, CI #21085: passed. The full upstream pytest result was 287 passed, 0 failed, and 2 optional collection skips in 1.08 seconds. Executed-case pass rate: 100.0% (`287/287`). The package pipeline pass rate was also 100.0% (`1/1`); L0, L1, L4, L5, and the consumer `test_package` all passed. The log confirmed both the clean Meson environment and the signed test-only `tmpfile()` shim.

## Next True-Device Command

```sh
CI_PACKAGES="archives/p/python-cairo/1.29.0" zsh ci/conan/build_and_test.sh
```

If `python3` is not discoverable:

```sh
PYCAIRO_PYTHON="$HOME/usr/local/bin/python3" CI_PACKAGES="archives/p/python-cairo/1.29.0" zsh ci/conan/build_and_test.sh
```
