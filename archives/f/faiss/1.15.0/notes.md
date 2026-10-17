# Notes — faiss 1.15.0 upstream C++ test run

**Date**: 2026-08-28
**Task**: Build & run upstream faiss v1.15.0 C++ tests against the prebuilt static `libfaiss.a` on OHOS aarch64.

## Environment

- **Host**: HarmonyOS localhost, HongMeng Kernel 1.12.0, aarch64 GNU/Linux (native aarch64).
- **Toolchain**: OHOS NDK clang-15 (`/data/service/hnp/bin/clang++`), target `aarch64-unknown-linux-ohos`, libc++, C++20.
- **Conan profile**: `ci/conan/profiles/ohos-aarch64` (`os=OHOS arch=armv8 compiler=clang/15 libc++ cppstd=17 Release`).
- **faiss source (READ ONLY)**: `/storage/Users/currentUser/.conan2/p/b/faiss3d545cfe9a874/b/`.
- **Built lib**: `…/build/Release/faiss/libfaiss.a` (static, `FAISS_OPT_LEVEL=generic`, `FAISS_ENABLE_SVS=OFF`, `BUILD_TESTING=OFF`).
- **`/tmp` is read-only** on this host → all temp files must live under `$HOME/tmp`.

## Test build setup

A standalone CMake project was created at `$HOME/tmp/faiss-test-build/` (built into its `build/` subdir with the Ninja generator). Rationale: the upstream `tests/CMakeLists.txt` uses `FetchContent` to download GoogleTest from GitHub at configure time. The prebuilt **GoogleTest 1.17.0** was already present in the conan cache at `/storage/Users/currentUser/.conan2/p/b/gtestd3a6fb4517e1a/p/` (matching the `ohos-aarch64` profile exactly: `arch=armv8 os=OHOS compiler=clang/15 libc++ cppstd=17 Release fPIC=True shared=False`), so it was linked directly — no network fetch was attempted or needed.

Key build-config decisions:
- `CMAKE_SYSTEM_NAME=Linux`, `CMAKE_SYSTEM_PROCESSOR=aarch64` (per task spec; matches the conan profile intent).
- `CMAKE_CXX_STANDARD=20` with `-fPIC -stdlib=libc++ -O3 -DNDEBUG -fopenmp=libomp` — mirrors the flags recorded in `libfaiss.a`'s `CMakeFiles/faiss.dir/flags.make`.
- Include path: the **faiss source tree** root (`-I<conan-build>/b`), not the installed header package. The installed headers (`…/p/include/faiss/`) are missing `faiss/cppcontrib/` (needed by `test_cppcontrib_sa_decode.cpp`/`test_cppcontrib_uintreader.cpp`) and `faiss/build.h` (needed by several tests). The source tree has all of these plus the generated `build.h`.
- `COMPILE_SIMD_ARM_NEON` + `FINTEGER=int` defined for all test TUs, matching the library build (the generic aarch64 `faiss` target was built with `COMPILE_SIMD_ARM_NEON` so `SIMDConfig` / `simdlib_dispatch.h` resolve the NEON backend consistently).
- Link order (matters for static archives): `libgtest.a` → `libgtest_main.a` → `libfaiss.a` → `libopenblas.so` → `libomp.a` → `libc++.a` → `libc++abi.a` → `-lpthread -ldl -lm`.

## The 6 excluded test files

1. `test_simd_levels_x86_avx2.cpp` — x86-only, raw AVX2 intrinsics (task exclude).
2. `test_simd_levels_x86_avx512.cpp` — x86-only, raw AVX512 intrinsics (task exclude).
3. `test_svs.cpp` — `FAISS_ENABLE_SVS=OFF` (task exclude).
4. `test_svs_metric.cpp` — `FAISS_ENABLE_SVS=OFF` (task exclude).
5. `test_rabitq_simd.cpp` — DD-only + x86 test (`tests/CMakeLists.txt` includes it only under `if(FAISS_OPT_LEVEL STREQUAL "dd")` AND `CMAKE_SYSTEM_PROCESSOR MATCHES x86`). It references `faiss::rabitq::rearrange_bit_planes<SIMDLevel::AVX2>` and `bitwise_and_dot_product_with_popcount<SIMDLevel::AVX2>` specializations that do not exist in the generic aarch64 library; the initial link failed on these undefined symbols. Excluded to match the upstream generic-mode `faiss_test` target.
6. `test_simd_perf.cpp` — DD-only test (`tests/CMakeLists.txt` includes it only under `if(FAISS_OPT_LEVEL STREQUAL "dd")`). Not part of the generic `faiss_test` target.

53 test files were compiled (the upstream generic-mode list of 41 base + 4 `NOT WIN32` = 45, plus 8 extra `.cpp` files that exist in the tree but aren't listed in the upstream `faiss_test` target — `test_binary_hash`, `test_distances_dispatch`, `test_io_corrupted`, `test_ivf_sharding`, `test_nndescent`, `test_omp_exception_safety`, `test_read_index_deserialize`, `test_sorting`). All compile cleanly.

## Build finding: NEON SIMD TUs missing from libfaiss.a

`libfaiss.a` was built with `CMAKE_SYSTEM_NAME=HarmonyOS` (the conan toolchain maps `os=OHOS` → `CMAKE_SYSTEM_NAME=HarmonyOS`). CMake has no `Platform/HarmonyOS` module, so it logs `System is unknown to cmake, create: Platform/HarmonyOS …` and **leaves `CMAKE_SYSTEM_PROCESSOR` unset/`unknown`**. Faiss's `faiss/CMakeLists.txt` chooses SIMD sources via:

```cmake
if(CMAKE_SYSTEM_PROCESSOR MATCHES "(x86_64|amd64|AMD64)")
  set(FAISS_SIMD_SRC ${FAISS_SIMD_AVX2_SRC} ${FAISS_SIMD_AVX512_SRC} ...)
elseif(CMAKE_SYSTEM_PROCESSOR MATCHES "(aarch64|arm64|ARM64)")
  set(FAISS_SIMD_SRC ${FAISS_SIMD_NEON_SRC} ${FAISS_SIMD_SVE_SRC})
…
else()
  set(FAISS_SIMD_SRC "")
endif()
```

With `CMAKE_SYSTEM_PROCESSOR=unknown`, none of the branches match, so `FAISS_SIMD_SRC` is empty — **no NEON SIMD TUs were compiled into `libfaiss.a`**. The 10 files in `FAISS_SIMD_NEON_SRC` (incl. `impl/approx_topk/neon.cpp`, `impl/fast_scan/impl-neon.cpp`, `impl/binary_hamming/neon.cpp`, `impl/pq_code_distance/neon.cpp`, `utils/simd_impl/distances_aarch64.cpp`, `utils/simd_impl/rabitq_neon.cpp`, …) are absent from the archive.

This caused the first link attempt to fail with undefined `faiss::HeapWithBucketsCMaxFloat<8u,3u,(faiss::SIMDLevel)4>::bs_addn` (and three siblings) — `SIMDLevel=4` is `ARM_NEON`, and its explicit template specializations live in `impl/approx_topk/neon.cpp`. These are referenced by `test_approx_topk.cpp` via `with_simd_level_256bit` dispatch.

**Workaround applied**: the 10 `FAISS_SIMD_NEON_SRC` files were compiled as an `OBJECT` library (`faiss_neon_tus`) in the test project and linked **before** `libfaiss.a`, supplying the missing ARM_NEON specializations. All compile cleanly with `COMPILE_SIMD_ARM_NEON` defined. After this, the full link of `faiss_test` (53 test TUs + 10 NEON TUs) succeeded.

**Proper fix** (implemented in conanfile): a CMake patch (`patches/fix-neon-simd-on-ohos.patch`) inserts an `if(CMAKE_SYSTEM_NAME STREQUAL "HarmonyOS" …) set(CMAKE_SYSTEM_PROCESSOR "aarch64")` block immediately after `project()` returns. The earlier attempt — `tc.variables["CMAKE_SYSTEM_PROCESSOR"]="aarch64"` in `generate()` — writes a `set(... CACHE STRING ...)` into `conan_toolchain.cmake`, but CMake's `project()` re-evaluates `CMAKE_SYSTEM_PROCESSOR` internally and overwrites the cache value to `unknown` on HarmonyOS (no Platform module). The patch runs *after* `project()`, so the override sticks: `flags.make` now shows `CXX_DEFINES = -DCOMPILE_SIMD_ARM_NEON -DFINTEGER=int`, and `ar t libfaiss.a` lists all 10 NEON `.o` files (`distances_aarch64.cpp.obj`, `impl-neon.cpp.obj`, `sq-neon.cpp.obj`, `neon.cpp.obj` ×3, `hamming_neon.cpp.obj`, `partitioning_neon.cpp.obj`, `simdlib_based_neon.cpp.obj`, `rabitq_neon.cpp.obj`). The `tc.variables` cache entry is kept as a belt-and-suspenders hint. This ensures NEON-optimised distance/hamming/fast-scan kernels are present in `libfaiss.a` for production use.

## Compile + link result

✅ **SUCCESS**. `faiss_test` is an ELF64 AArch64 dynamically-linked executable (23 MB, not stripped), `NEEDED`: `libopenblas.so.0`, `libomp.so`, `libc++_shared.so`, `libc.so`. RUNPATH set to the OpenBLAS and OHOS LLVM lib dirs so it loads without manual `LD_LIBRARY_PATH` (though `LD_LIBRARY_PATH` is still used below for the `/tmp` shim).

Only one harmless warning across all 63 compiled TUs: `'COMPILE_SIMD_NONE' macro redefined` — `faiss/utils/simd_levels.h` line 17 does `#define COMPILE_SIMD_NONE` unconditionally; removed the redundant `-DCOMPILE_SIMD_NONE` from the test compile definitions to silence it.

## Runtime result

The binary runs natively (`./faiss_test --help` works). Running the full 508-case suite aborts early because **5 test files hardcode temp-file paths under `/tmp`** and `/tmp` is read-only:

- `test_merge.cpp`: `std::string temp_filename_template = "/tmp/faiss_tmp_XXXXXX";` (used by `MERGE.merge_flat_ondisk*`).
- `test_ondisk_ivf.cpp`: `std::string filename = "/tmp/faiss_tmp_XXXXXX";` (used by `ONDISK.*`).
- `test_ivf_sharding.cpp`: `Tempfilename prefix(&temp_file_mutex, "/tmp/faiss_ivf_shard_XXXXXX");`.
- `test_disable_pq_sdc_tables.cpp`: `"/tmp/faiss_TestReadHNSWPQ" + …` (suite `IO`).
- `test_mmap.cpp`: `std::tmpnam(nullptr)` (returns a `/tmp/...` path on this libc).

A custom `LD_PRELOAD` shim (`$HOME/tmp/tmp_shim.so`, built with the OHOS clang) intercepts `open/open64/creat/fopen/mkstemp/tmpnam/access/unlink/mkdir/truncate/stat/lstat/rename` and rewrites any path beginning with `/tmp/` to `/storage/Users/currentUser/tmp/`. This unblocks file creation (the `fopen("w")` + `truncate()` calls succeed), but the `OnDiskInvertedLists::do_mmap()` path then segfaults (SIGSEGV) right after `fopen("r+")` + `mmap(MAP_SHARED, fileno(f), 0)`. A minimal C reproducer of the exact `mkstemp→close→fopen(w)→fclose→truncate→fopen(r+)→mmap(MAP_SHARED)→munmap→truncate→fopen(r+)→mmap` sequence **succeeds in isolation**, so the crash is specific to the faiss OnDiskInvertedLists code path under the musl/hmdfs runtime — an environment-specific runtime failure, not a general mmap/filesystem problem and not a compile defect. (Ptrace is denied on this host, so a gdb backtrace could not be captured; core dumps cannot be written because `/` is read-only.)

To obtain a clean pass/fail tally, the 14 cases in the `/tmp`-dependent suites were excluded via `--gtest_filter='*-MERGE.*:ONDISK.*:TestIvfSharding.*:TestMmap.*:IO.*'` and the remaining 494 cases ran to completion:

- **PASSED: 482**
- **SKIPPED: 11** — all `GTEST_SKIP()` because the generic/static build only makes `SIMDLevel::ARM_NEON` (and `NONE`) available; the AVX2/AVX512/ARM_SVE levels the tests exercise are not compiled in. Affected: `ScalarQuantizer.TQMSESimdDispatchSelection`, `ScalarQuantizer.EDENSimdDispatchSelection`, `ScalarQuantizer.TQMSESimdDistancePathParity`, `ScalarQuantizer.EDENSimdDistancePathParity`, `SIMDConfig.modern_hardware_has_simd_support`, and the six `DistancesDispatch.Fvec*` tests.
- **FAILED: 1** — `ReadIndexDeserialize.SVSVamanaFourccRejected`. This test is in the `#else // !FAISS_ENABLE_SVS` branch (so it's meant to run when SVS is off). It feeds the deserializer a buffer tagged with the `ISVD` fourcc and expects the thrown `FaissException` message to contain the substring `"fourcc"`. The library instead emits `"Index type 0x44565349 (\"ISVD\") not recognized"` (from `faiss/impl/index_read.cpp:3153`), which does **not** contain `"fourcc"`. Genuine library-vs-test mismatch in the SVS-disabled configuration — the test's expected error substring doesn't match the message the implementation actually produces.

## Files produced

- `$HOME/tmp/faiss-test-build/CMakeLists.txt` — standalone test-build project (links the prebuilt `libfaiss.a` + the `faiss_neon_tus` OBJECT lib of the 10 missing NEON TUs).
- `$HOME/tmp/faiss-test-build/build/faiss_test` — the built test executable (AArch64 ELF).
- `$HOME/tmp/tmp_shim.c` / `$HOME/tmp/tmp_shim.so` — `LD_PRELOAD` `/tmp`→`$HOME/tmp` redirect shim source + compiled .so.
- `archives/f/faiss/1.15.0/reports/upstream-tests.md` — this run's detailed report.
- `archives/f/faiss/1.15.0/manifest.yaml` — `test_results:` section added.
- `archives/f/faiss/1.15.0/notes.md` — this file.

## Recommendations

1. **Fix the library build's SIMD source selection**: ensure `CMAKE_SYSTEM_PROCESSOR=aarch64` when building for HarmonyOS/aarch64, so `FAISS_SIMD_NEON_SRC` is populated and the NEON-optimised kernels are linked into `libfaiss.a`. This both removes the need for the `faiss_neon_tus` workaround in the test build and gives production users the ARM-NEON fast paths (distances, hamming, fast-scan, RaBitQ, approx_topk).
2. **Make the 5 `/tmp`-dependent tests honor `TMPDIR`** (or use `$TMPDIR/faiss_…` instead of hardcoded `/tmp/…`). This would let them run on any host with a writable temp dir and is the upstream-portable fix.
3. **Investigate the `OnDiskInvertedLists` mmap segfault** under musl/hmdfs separately (only reachable once `/tmp` is writable). Likely a subtle interaction between repeated `mmap`/`munmap` of a `MAP_SHARED`-mapped `hmdfs` file and the faiss `update_totsize`/`do_mmap` resize logic.
4. **Fix `test_read_index_deserialize.cpp:SVSVamanaFourccRejected`**: change the expected substring from `"fourcc"` to something present in the actual SVS-disabled rejection message (e.g. `"not recognized"`), or have the library emit a `"fourcc"`-containing message for unknown fourccs.
