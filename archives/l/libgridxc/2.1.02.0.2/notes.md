# libgridxc 2.1.02.0.2 adaptation notes

## Version mapping

- Task version `2.1.02.0.2` sanitizes Debian `2.1.0+really2.0.2`.
- Debian `+really` means the payload is upstream `2.0.2`, not `2.1.0`.
- Recipe therefore downloads upstream tag `2.0.2`:
  `https://gitlab.com/siesta-project/libraries/libgridxc/-/archive/2.0.2/libgridxc-2.0.2.tar.gz`
- SHA256 `ce7e3de5b1232e63bc953a994f549411edb90c22b22f9b7749d8f2a79d3c1a98` was computed
  locally from the GitLab archive on 2026-09-21 and must match the true-machine download.
- Upstream tag `2.1.0` SHA256 `da5c484090c2a96dece65bb7e70f0c0bf278fe9c4649e9f8326508adbe05df1e`
  is recorded here only to prove the payload choice; it is not used by the recipe.

## Upstream inventory

- Build systems: CMake (`CMakeLists.txt`, `src/CMakeLists.txt`, `Testers/CMakeLists.txt`)
  and Autotools (`Makefile.am`, `src/Makefile.am`, `Testers/Makefile.am`).
- Recipe uses CMake because it exposes `WITH_MPI`, `WITH_LIBXC`, `WITH_GRID_SP`,
  installs CMake package files, and registers ctest entries deterministically.
- Upstream `Testers/CMakeLists.txt` registers via `define_test`:
  `test1`, `test2`, `test3`, `test4`, `test6` unconditionally (5 entries),
  plus `test_libxc`, `test_libxc2`, `test_match`, `test_hse06` inside
  `if (WITH_LIBXC)` (4 conditional entries, 9 total). `test5` is pending
  refactoring and is never registered. Upstream default is
  `option(WITH_LIBXC ... FALSE)`, so a default-configure `ctest -N`
  discovers 5; the full `ctest_entries`口径 total including the
  conditional block is 9.
- Autotools `Testers/Makefile.am` registers `test1`, `test2` plus `test3`, `test4`
  without MPI (4 entries), plus 4 libxc entries with libxc. `test6` is CMake-only.
- Declared `upstream_test_total`: 9, method `ctest_entries`, from
  `Testers/CMakeLists.txt` all 9 `define_test` lines in the 2.0.2 payload
  (5 unconditional + 4 WITH_LIBXC-conditional). Recipe keeps upstream
  default `WITH_LIBXC=OFF`, so `ctest -N` on device discovers 5 and all 5
  run; the remaining 4 are configuration-excluded by the same option, not
  by missing files or skipped assertions.
- Recipe sets `WITH_MPI=OFF`, `WITH_LIBXC=OFF`, `WITH_GRID_SP=OFF`:
  no MPI runtime and no libxc package are required on the device.
  Serial `gridxc_init()` is therefore exercised; MPI parallel paths are not claimed.

## Build design

- Follows `archives/l/lapack/3.12.1` and `archives/s/scalapack/2.2.3`:
  `tool_requires flang-ohos/20.1.0`, `CMAKE_Fortran_COMPILER` points at the
  flang package, OHOS sysroot/resource-dir/lib are taken from the device SDK,
  `CMAKE_TRY_COMPILE_TARGET_TYPE=STATIC_LIBRARY` lets CMake configure checks
  pass with the reduced flang runtime.
- `CMAKE_EXE_LINKER_FLAGS` and `CMAKE_SHARED_LINKER_FLAGS` explicitly add
  SDK `aarch64-linux-ohos` lib plus flang `lib` with
  `-lFortranRuntime -lFortranDecimal -lm`, so both the shared library and the
  ctest executables link against a visible Fortran runtime.
- The built `libgridxc` shared/static library plus `libFortranRuntime.a` and
  `libFortranDecimal.a` are packaged together; consumers link
  `gridxc`, `FortranRuntime`, `FortranDecimal`, `m`.
- ELF signing follows scalapack: every ET_EXEC/ET_DYN under build and package
  trees is re-signed with `llvm-objcopy` plus `binary-sign-tool`, verified by
  exactly one `.codesign` section in `llvm-readelf -SW`.
- No source patch is declared. No `__OHOS__` macro is introduced.

## Test design

- Upstream: `ctest --output-on-failure` runs in `build()` after signing.
  `ctest -N` provides `discovered`; per-line `Test #N ... Passed|Failed` parsing
  provides `executed/passed/failed/skipped`. Counts come from a single parse
  without arithmetic repair. Result is printed as `HMBS_UPSTREAM_TEST_RESULT`
  JSON and persisted to `hmbs_upstream.json`, then shipped in `res/` so
  `test_package` can re-emit it on cache-hit rounds.
- Consumer: two Fortran programs link `libgridxc::libgridxc`:
  1. `lda_contract` calls `gridxc_init`, `gridxc_setXC` LDA/PZ, `gridxc_getXC`
     round-trip, then `gridxc_ldaxc` PZ at density 0.01 and asserts finite
     negative exchange/correlation potentials.
  2. `gga_contract` calls `gridxc_init`, `gridxc_setXC` GGA/PBE, then
     `gridxc_ggaxc` PBE at density 0.01 plus small gradient and asserts finite
     negative exchange energy per electron.
- Each consumer prints exactly one `GRIDXC_TEST <name> PASS` line only after all
  assertions succeed. `test()` signs OHOS ELFs, runs both, then prints
  `HMBS_TEST_PACKAGE_RESULT` with `discovered=2/passedCount=2` and re-emits the
  persisted upstream JSON.

## Evidence status

- First round: working tree only, no true-machine run yet.
- Awaiting HMBS preflight `conan create` log for real
  `executed/passed` numbers. PR body test counts are left for the evidence round.

## 2026-09-21 Signal 9 empty-log mitigation

- Preflight failed at compile with bare Signal 9 and empty stdout/stderr tail.
- Applied additive low-memory mitigation only: CFLAGS/CXXFLAGS/FFLAGS/FCFLAGS append -O1 -g0, CMAKE_C/Fortran_FLAGS append -O1 -g0, linker flags append -g0, generated conan_toolchain.cmake appended behind idempotent HMBS_LOW_MEM_BEGIN/END marker covering base plus RELEASE/RELWITHDEBINFO/MINSIZEREL/DEBUG per-config flags so trailing -O1 -g0 wins over profile -O3/-g without overwriting profile content.
- Kept WITH_MPI/WITH_LIBXC/WITH_GRID_SP OFF and all ctest/test_package assertions unchanged.

## 2026-09-24 L5 SONAME gate fix (CI #57764)

- CI failed L5: `libgridxc.so missing DT_SONAME` + `IMPORTED_NO_SONAME TRUE`
  in `libgridxc-targets-release.cmake` (`L5_RESULT=fail: soname_gate_failed`).
  Upstream `CMakeLists.txt` already sets `VERSION 2.0.2 / SOVERSION 2` on
  `libgridxc-lib` (OUTPUT_NAME gridxc), so no source patch is needed.
- Root cause is platform-only: CMake has no `Platform/HarmonyOS.cmake`, so
  `CMAKE_SHARED_LIBRARY_SONAME_*_FLAG` is empty and the linker never gets
  `-Wl,-soname` (same dual cause as libharu draft + scalapack/2.2.3).
- Fix is toolchain-only in `generate()`: when `shared=True`, set
  `CMAKE_PLATFORM_NO_VERSIONED_SONAME=True` plus
  `CMAKE_SHARED_LIBRARY_SONAME_C/CXX/Fortran_FLAG="-Wl,-soname,"`
  (Fortran flag is the decisive one; C/CXX kept for completeness).
  Produces unversioned `libgridxc.so` with relative SONAME, no version symlinks.

## 2026-09-24 rule4 evidence fix (executed 0 vs passed)
- Symptom: HMBS_UPSTREAM_TEST_RESULT status passed with discovered=5 executed=0 passed=0.
- Root cause: _parse_ctest_output only matched `Passed`/`Failed` after dots and exact tokens; ctest failure lines use `***Failed`/`***Timeout`/`***Not Run` without dots, so failures parsed as 0 and `failed==0` wrongly mapped to passed.
- Fix: single-source `_parse_ctest_lines` strips ANSI, matches status word after `Test #N:` (Timeout/Failed/Passed/Skipped/Not Run/Disabled), prefers Testing/Temporary/LastTest.log when it carries results else stdout, never derives counts from returncode; zero-result now emits status failed with searched paths and raises; added gaps disclosure when skipped/missing under passed.

## 2026-09-28 rule4 gaps disclosure (5/9 conditional registration)

- Symptom: preflight evidence incomplete — HMBS_UPSTREAM_TEST_RESULT discovered=5
  executed=5 passed=5 with no gaps, while declared upstream_test_total=9
  (ctest_entries); gate requires gaps covering total-passed=4.
- Root cause: recipe-only evidence gap, not a test failure. The 4 missing entries
  (test_libxc, test_libxc2, test_match, test_hse06) are defined only inside
  if(WITH_LIBXC) in Testers/CMakeLists.txt; recipe keeps upstream
  option(WITH_LIBXC) default FALSE, so ctest -N discovers 5 and all 5 pass.
  _run_upstream_ctest only emitted gaps for skipped/missing within discovered,
  never for unregistered conditional entries.
- Fix (conanfile.py only, no source/test change): in _run_upstream_ctest, after
  the deterministic LastTest.log/stdout parse, disclose unregistered =
  upstream_total(9) - discovered with category environment, naming the 4
  conditional tests, the WITH_LIBXC=OFF default, and evidence
  Testers/CMakeLists.txt if(WITH_LIBXC) block + ctest -N count. Gaps sum now
  equals 9-5=4. Single-source parsing and all invariants unchanged.

## 2026-09-24 ctest RUNPATH fix (5/5 symbol-not-found)
- Symptom: 5/5 ctest failed with "Error loading shared library libgridxc.so" + "Error relocating ... _QMgridxc_cellPcellxc/_QMgridxc_ggaPggaxc/_QMgridxc_ldaPldaxc: symbol not found".
- Root cause: platform-only loader lookup, not source symbols. CMake has no Platform/HarmonyOS module so build RPATH is empty; Testers executables could not resolve the just-built build-tree libgridxc.so at ctest time.
- Fix (toolchain + runner, no source/test change): (1) generate() wires $ORIGIN-relative RUNPATH (RUNTIME_FLAG/-rpath/, SEP :, RPATH_LINK_FLAG/-rpath-link/, RPATH_ORIGIN_TOKEN $ORIGIN, BUILD_RPATH_USE_ORIGIN True for C/CXX/Fortran, mirroring scalapack/2.2.3); (2) _run_upstream_ctest() prepends every build-tree dir holding libgridxc.so* plus flang lib to LD_LIBRARY_PATH for the ctest subprocess and logs it. Neither skips tests nor edits assertions.

## 2026-09-28 low-mem toolchain flag injection fix (flang -g0+low+)
- Symptom: CMake Fortran compiler check broken: flang invoked with -O1 -g0+low+, error unknown argument -g0+low+.
- Root cause: _patch_toolchain_low_mem built the CMake block from adjacent literals QUOTE string(APPEND CMAKE_Fortran_FLAGS QUOTE QUOTE + low + QUOTE etc, so Python concatenated them literally and the toolchain file received string(APPEND ... + low +) which CMake APPEND turned into +low+ appended to flags. The low variable was never interpolated.
- Fix (conanfile.py only): build the block with explicit Python concatenation in a loop over the 15 C/CXX/Fortran base+config flag vars, producing string(APPEND <VAR> " -O1 -g0") plus add_compile_options(-O1 -g0); verified zero remaining literal low tokens and file parses.
