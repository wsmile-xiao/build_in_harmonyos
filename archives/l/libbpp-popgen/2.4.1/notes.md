# libbpp-popgen 2.4.1 notes

## Scope

Bio++ Population Genetics library (`Bpp/PopGen`), release tag `v2.4.1` of
<https://github.com/BioPP/bpp-popgen>. It provides the genotype/allele data
model (`DataSet`, `Individual`, `Group`, `Locality`, `LocusInfo`,
`AlleleInfo`), monolocus/multilocus genotype classes, population-statistics
helpers and the Genepop / Genetix / Darwin / Popgenlib readers and writers.
Sibling package of the already-archived `libbpp-core/2.4.1` and
`libbpp-seq/2.4.1`.

## Upstream build facts (verified against the tarball)

- `CMakeLists.txt`: `cmake_minimum_required(VERSION 2.8.11)`,
  `project(bpp-popgen CXX)`, `PACKAGE_VERSION 8.0.0` (SOVERSION 8).
- `src/CMakeLists.txt` builds **both** `bpp-popgen-static` and
  `bpp-popgen-shared` (`OUTPUT_NAME bpp-popgen`) and installs both, together
  with `Bpp/PopGen` headers and its own `bpp-popgen-config.cmake`
  (`install(EXPORT ...)` + `package.cmake.in`).
- Dependency: `find_package(bpp-seq 12.0.0 REQUIRED)`. `12.0.0` is bpp-seq's
  **API version** (`PACKAGE_VERSION` in its config), not its release tag
  (2.4.1). `bpp-seq-config.cmake` in turn requires
  `find_package(bpp-core 4.1.0 REQUIRED)`.
- **No test suite**: the tarball has no `tests/` or `test/` directory
  (top level: `AUTHORS.txt CMakeLists.txt COPYING.txt ChangeLog Doxyfile
  INSTALL.txt bpp-popgen.spec header.html package.cmake.in src`). Upstream
  registered test count is therefore **N = 0**.

## Dependency resolution

`libbpp-seq/2.4.1` is published in the ohpcd registry as a **static** package
(`shared=False`, clang 15 / libc++ / OHOS armv8) and ships, in one package:

```
include/Bpp/...                     (bpp-seq + bpp-core headers)
lib/libbpp-seq.a
lib/libbpp-core.a
lib/cmake/bpp-seq/bpp-seq-config.cmake   (+ -targets / -version)
lib/cmake/bpp-core/bpp-core-config.cmake (+ -targets / -version)
res/upstream_test_result.json
```

So a single `requires("libbpp-seq/2.4.1")` satisfies upstream's
`find_package(bpp-seq 12.0.0)` and the nested `find_package(bpp-core 4.1.0)`.
The recipe points `CMAKE_PREFIX_PATH` at that package folder (the upstream
`bpp-*-config.cmake` files live under `lib/cmake/<name>/`, which CMake searches
below each prefix entry) and nothing has to be vendored.

## OHOS adaptation summary

1. **CMake policy floor** — upstream declares `cmake_minimum_required(VERSION
   2.8.11)`; modern CMake refuses such projects. `CMAKE_POLICY_VERSION_MINIMUM=3.5`
   is pinned in the toolchain so the project configures in compatibility mode.
2. **PIC / shared toggle** — `BUILD_SHARED_LIBS` follows the `shared` option and
   `CMAKE_POSITION_INDEPENDENT_CODE` follows `shared or fPIC`, matching the
   `libbpp-seq` / `libbpp-core` recipes.
3. **Prune the unrequested variant** — upstream installs the static+shared pair
   unconditionally. With `shared=False` the `.so*` files are removed in
   `package()` so a consumer cannot resolve a shared object that the package
   options did not promise (family convention, `libbpp-seq` precedent).
4. **RPATH** — `CMAKE_INSTALL_RPATH=$ORIGIN` is set so the shipped libraries
   stay relocatable if they are ever used together in one directory.
5. **Consumer test links static archives by absolute path** — the test_package
   CMakeLists pins `libbpp-popgen.a` + `libbpp-seq.a` + `libbpp-core.a`, so the
   test binary has **zero runtime `.so` dependency**. It therefore runs both on
   the device/CI worker and on a cross-build host with a working aarch64
   loader.

## Tests

Upstream ships none (N = 0). Following the platform rule ("上游没有测试用例时，
按公开 API 设计真实测试，说明覆盖接口、执行命令和结果"), the recipe does **not**
invent upstream cases; coverage lives in `test_package/`:

`test_package/test_bpp_popgen.cpp` — 31 assertions over the public API:

| group | assertions |
|---|---|
| `BasicAlleleInfo` (identifier round trip, `setId`, equality, inequality, `clone`) | 5 |
| `MonoAlleleMonolocusGenotype` / `BiAlleleMonolocusGenotype` / `MultiAlleleMonolocusGenotype` (allele indices, homozygosity) | 8 |
| `LocusInfo` (name, ploidy constant, allele registration, key lookup, `BadIdentifierException`, `AlleleNotFoundException`) | 7 |
| `AnalyzedLoci` (locus count, name lookup, allele counts, ploidy, `addAlleleInfoByLocusPosition`) | 5 |
| `DataSet` / `Group` / `Individual` (group + individual add/find/delete) | 5 |
| `Bpp/Version.h` fingerprint | 1 |

All checks are deterministic: no input files, no network, no device, no
`LD_LIBRARY_PATH`. The test is registered with ctest
(`add_test(NAME test_bpp_popgen ...)`) and executed by `ctest --output-on-failure`
from `test()`, which also provides the CI test-execution evidence.

## Verification

```
$ conan create . -pr:h=ohos-aarch64 -pr:b=default      # 本地：源码镜像 file://
...
[ 98%] Linking CXX static library libbpp-popgen.a
libbpp-popgen/2.4.1: Created package revision ...
conan create exit=0
```

Package layout produced (verified in the cache):

```
include/Bpp/PopGen/**.h
lib/libbpp-popgen.a                     (the .so variant is pruned)
lib/cmake/bpp-popgen/bpp-popgen-config.cmake (+ targets / version)
licenses/COPYING.txt
res/upstream_test_result.json
```

The consumer test is executed on the **OHOS aarch64 ABI** on this host by
linking it fully static (the three shipped archives plus the SDK's static
`libc++.a` / `libc++abi.a` / `libunwind.a`) and running it under
`qemu-aarch64-static` — no OHOS dynamic loader is needed because the resulting
ELF has no `INTERP` segment:

```
$ scripts/ohos/verify-libbpp-popgen-runtime.sh
/tmp/test_bpp_popgen_static: ELF 64-bit LSB executable, ARM aarch64, statically linked
INTERP 段数量（0 = 全静态）: 0
PASS: BasicAlleleInfo stores the identifier given at construction
...
PASS: the Bio++ version header is usable from the packaged includes
----------------------------------------
checks: 31  failures: 0
ALL PASS
consumer exit=0
```

`test()` itself runs `ctest --output-on-failure` on the target (the CI worker
executes the binary natively); on a cross-building host without a loader the
consumer is compiled and linked, and the run is deferred.

## Patches

| patch | purpose |
|---|---|
| `0001-cmake-use-conan-libbpp-seq-target.patch` | Replaces `find_package(bpp-seq 12.0.0 REQUIRED)` with the Conan target `libbpp-seq::libbpp-seq`. Reason: the published `libbpp-seq/2.4.1` package prunes its `.so` (static delivery) while still shipping the upstream `bpp-seq-targets.cmake` / `bpp-core-targets.cmake`, and CMake validates every file registered in those files — so the upstream config aborts with *"The imported target \"bpp-core-shared\" references the file ... which does not exist"*. The Conan target carries the same headers, the same static archives and the same transitive bpp-core link. |
| `0002-cpp17-random-shuffle-compat.patch` | `std::random_shuffle` was removed in C++17 and is not provided by OHOS's libc++ 15 while the profile builds with `-std=c++17`. Adds a local `bppRandomShuffle` (the historical libstdc++ implementation: Fisher-Yates driven by `std::rand()`) and redirects the five call sites in `PolymorphismMultiGContainerTools.cpp`, keeping the sampling behaviour unchanged. |

Both patches apply cleanly (`patch -p1 --dry-run` → exit 0) and touch no test
sources (upstream ships none).
