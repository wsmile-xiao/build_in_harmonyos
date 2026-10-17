# nextpnr 0.1

## Scope

Builds `nextpnr-ice40` for OpenHarmony PC (aarch64) from the upstream
`nextpnr-0.1` release tarball, with the iCE40 device databases produced at
build time from the `icestorm` package.

Options:

- `arch` = `ice40` (default) or `generic`.
- `build_tests` = `False` (default). See "Upstream tests" below.

## Build-time code generation

`nextpnr-ice40` does not ship its device database as source. It is generated
during the build, in two stages:

```
ice40/chipdb.py  (build-machine Python)   chipdb-<dev>.txt  ->  chipdb-<dev>.bba
bbasm            (build-machine executable) chipdb-<dev>.bba ->  chipdb-<dev>.cc
OHOS clang++     (target compiler)          chipdb-<dev>.cc  ->  object -> link
```

`ice40/chipdb.py` reads `<ICEBOX_DATADIR>/chipdb-<device>.txt` plus the
IceStorm timing tables, which the `icestorm` package installs under
`share/icebox/`. This is why the recipe depends on `icestorm/1.1.1`: 1.1
packaged no `chipdb-*.txt` at all, so the codegen step could not run.

## Finding: this is NOT a dual-toolchain (cross-compilation) situation

Upstream guards the build-machine executable with
`nextpnr/CMakeLists.txt:238`:

```cmake
if(CMAKE_CROSSCOMPILING)
    set(BBA_IMPORT "IMPORTFILE-NOTFOUND" CACHE FILEPATH ...)
    include(${BBA_IMPORT})
else()
    add_subdirectory(bba)
endif()
```

On this platform that guard is **never taken**. Measured on the HarmonyOS PC
with the farm's `ohos-aarch64` Conan profile:

| Observation | Value |
|---|---|
| `main-build/bba/CMakeFiles/bbasm.dir` | present -> the `else()` branch ran |
| `CMAKE_SYSTEM_NAME` in `conan_toolchain.cmake` | not set at all |
| `-DBBA_IMPORT=...` passed explicitly | CMake reports it as an **unused** variable |
| Compiler used for `bbasm` | `/storage/.../.harmonybrew/bin/clang++ -stdlib=libc++` |

The build machine is HarmonyOS aarch64 and the target is OHOS aarch64 - the
same platform. Conan's OHOS profile does not set a `CMAKE_SYSTEM_NAME` that
differs from the detected host system (`HarmonyOS`), so CMake does not consider
this a cross-compilation, `add_subdirectory(bba)` runs, and `bbasm` is simply
built with the OHOS compiler - which is directly runnable on the same machine.

**The `BBA_IMPORT` mechanism is therefore not exercised here and is not used by
this recipe.** The "host toolchain vs target toolchain separation" that the
codegen chain suggests does not exist on OHOS. What *is* real is that the
build-machine executable has to be runnable at build time - see the next
section, where that fails for a different reason.

## Finding: the build-machine executable cannot load its shared dependencies

`bbasm` is compiled during the build and then **run** during the same build.
It linked successfully but could not start:

```
Error loading shared library libboost_program_options.so: (needed by ./main-build/bba/bbasm)
Error loading shared library libboost_container.so: (needed by ./main-build/bba/bbasm)
Error loading shared library libboost_filesystem.so: (needed by ./main-build/bba/bbasm)
Error relocating bba/bbasm: _ZNK5boost15program_options22error_with_option_name4whatEv: symbol not found
make[3]: *** [CMakeFiles/chipdb-ice40-bins.dir/build.make:74: ice40/chipdb/chipdb-1k.cc] Error 127
```

Root cause, from the produced binary:

```
$ readelf -d main-build/bba/bbasm | grep -E 'NEEDED|RUNPATH'
 0x0000000000000001 (NEEDED)  Shared library: [libboost_program_options.so]
 0x0000000000000001 (NEEDED)  Shared library: [libboost_container.so]
 0x0000000000000001 (NEEDED)  Shared library: [libboost_filesystem.so]
 0x0000000000000001 (NEEDED)  Shared library: [libboost_atomic.so]
 0x0000000000000001 (NEEDED)  Shared library: [libc++_shared.so]
 0x0000000000000001 (NEEDED)  Shared library: [libc.so]
        <-- no RUNPATH / RPATH entry at all
```

Two things combine:

1. ohpcd ships Boost as **shared-only** (19 `.so`, 1 `.a` in the package `lib/`),
   so `bbasm` genuinely needs those libraries at runtime.
2. CMake has **no `Platform/HarmonyOS` module** - configure-time message:
   `System is unknown to cmake, create: Platform/HarmonyOS ...`. RPATH link
   options come from the platform module, so CMake never emits one and the
   binary is linked without any runtime search path.

The same root cause was independently observed on `sonnet` in this repository
(cross-compiled shared libraries ending up without SONAME/RPATH handling), so
this is not specific to nextpnr - it affects any package that either runs a
generated helper at build time or ships a shared-library-dependent binary.

Fix: declare the dependency library directories as RPATH via
`tc.extra_exelinkflags` / `tc.extra_sharedlinkflags`, which append rather than
overwrite the flags Conan already set:

```python
tc.extra_exelinkflags.append("-Wl,-rpath,%s" % path)
```

Result after the fix, same binary:

```
$ readelf -d main-build/bba/bbasm | grep RUNPATH
 0x000000000000001d (RUNPATH)  Library runpath: [.../boost34a803394a31c/p/lib]

$ ./main-build/bba/bbasm
Endian parameter is mandatory          <- its own usage error; the binary started
```

With that in place the whole chain runs (measured on the HarmonyOS PC):

```
[ 25%] Generating chipdb/chipdb-1k.bba      <- build-machine Python step
[100%] Generating ice40/chipdb/chipdb-1k.cc  <- bbasm step
[100%] Building CXX object CMakeFiles/chipdb-ice40.dir/ice40/chipdb/chipdb-1k.cc.obj
[100%] Built target chipdb-ice40             <- OHOS target compiler
```

`chipdb-1k.bba` is 93 MB and the generated `chipdb-1k.cc` is 41 MB.

## Finding: does not compile against the Boost in ohpcd

nextpnr 0.1 (2021) predates two Boost removals:

- Boost 1.91 removed `boost/filesystem/convenience.hpp`
- Boost 1.84 removed `boost::filesystem::basename()`

```
bba/main.cc:22:10: fatal error: 'boost/filesystem/convenience.hpp' file not found
```

Only two files and three call sites are affected, handled by
`patches/0001-boost-1.91-filesystem-compat.patch`.

**Semantics matter here.** `boost::filesystem::basename(p)` was the old
convenience API that returned `p.stem()` - the filename *without* extension,
complementing `extension()` - not "strip the directory". The patch therefore
uses `boost::filesystem::path(p).stem().string()`. A helper that merely strips
the directory would return `chipdb-1k.bin` where the removed call returned
`chipdb-1k`, i.e. it would silently change the generated `#embed_str` name in
`--embed` mode. Getting this wrong is invisible as long as only the default
`BBASM_MODE=string` path is exercised.

`patches/0002-bba-modern-boost-targets.patch` fixes a second, related problem:
`bba/CMakeLists.txt` links the legacy `Boost_PROGRAM_OPTIONS_LIBRARY` /
`Boost_FILESYSTEM_LIBRARY` / `Boost_SYSTEM_LIBRARY` variables. Those are only
populated by CMake's `FindBoost` module. When Boost is located through
`BoostConfig.cmake` - which is what `CMakeDeps` arranges - they stay empty, so
`bbasm` would link without Boost and only fail later, at link or run time.

## Finding: same legacy-variable problem for Eigen (BUILD_HEAP)

The analytic placer hits the identical failure family one level up:

```
common/placer_heap.cc:37:10: fatal error: 'Eigen/Core' file not found
make[2]: *** [CMakeFiles/nextpnr-ice40.dir/build.make:317: ...placer_heap.cc.obj] Error 1
```

The top-level CMakeLists does:

```cmake
find_package(Eigen3 REQUIRED NO_MODULE)
include_directories(${EIGEN3_INCLUDE_DIRS})
```

`NO_MODULE` forces config mode, where `CMakeDeps` defines the imported target
`Eigen3::Eigen` but never the legacy all-caps `EIGEN3_INCLUDE_DIRS` variable, so
`include_directories()` adds nothing and the include fails. The recipe supplies
the variable from the dependency's own `cpp_info.includedirs`, which is what
fixes it; no patch to upstream is needed.

So both Boost and Eigen in this 2021 tree are consumed through legacy
`Find<Package>` variables, while a modern Conan dependency graph only provides
config-mode imported targets. Any recipe building this kind of older CMake
project has to bridge that gap explicitly.

## Finding: CMake 4.x rejects the vendored build files

`cmake_minimum_required` in the vendored tree: googletest `2.6.2`,
sanitizers-cmake `2.8`, pybind11 `3.4`. CMake 4.x removed compatibility with
anything below 3.5 and aborts at configure time. The recipe sets
`CMAKE_POLICY_VERSION_MINIMUM=3.5`. (ohpcd publishes no `cmake` package, so the
system CMake 4.1.2 on the worker is what runs.)

## Other configuration

- `ARCH` is mandatory - nextpnr has no default architecture
  (`Architecture setting is mandatory`).
- `USE_IPO=OFF`: the default `USE_IPO=ON` turns on
  `CMAKE_INTERPROCEDURAL_OPTIMIZATION`, which is not usable for the very large
  generated chipdb objects with the OHOS Clang 15 driver.
- `BUILD_GUI=OFF`: the GUI needs Qt5 (not published for OHOS), and setting it
  forces `BUILD_PYTHON=ON` as well.
- `BUILD_PYTHON=OFF`: would need libpython plus pybind11 building for OHOS.
- `CURRENT_GIT_VERSION`: the top-level CMakeLists runs
  `git describe --tags --always` at configure time; a release tarball is not a
  git checkout, so the value is supplied instead.
- `BUILD_HEAP=ON` (the analytic placer) needs Eigen, hence the `eigen/3.4.1`
  dependency.

## Upstream tests

`tests/` is a **git submodule** (`YosysHQ/nextpnr-tests`). The release tarball
contains that directory but with **zero files in it**, so `BUILD_TESTS=ON`
wires `aux_source_directory(tests/ice40/ ...)` to nothing and produces a test
binary with no cases. The suite is simply not obtainable from the release
tarball; the submodule would have to be fetched separately, and the recipe must
not download sources during `build()`.

Upstream test count claimed as executed: **0**. The `test_package` consumer
test below is what actually exercises the installed binary.

## Verification

Performed on the HarmonyOS PC (aarch64, OHOS 6.0, Clang 15.0.4) in a scratch
tree, using the farm's `ohos-aarch64` profile and the ohpcd `boost/1.91.0.1.3`
package, before the recipe was written:

- Boost patches apply cleanly (`patch` on the worker is a reduced
  implementation: `-p`, `-i`, `-R`, `-l`, `-s`, `--dry-run` only, no
  `-N/--forward`; it does apply atomically per file).
- `bbasm` builds and, after the RPATH fix, runs.
- `chipdb-1k.bba` (93 MB) and `chipdb-1k.cc` (41 MB) are produced.
- The generated `.cc` compiles with the OHOS compiler and links into the
  `chipdb-ice40` object library.

A full `conan create` through the farm verify pipeline, plus the consumer test
against the packaged binary, is recorded in `test_package/MANIFEST.yml`.
