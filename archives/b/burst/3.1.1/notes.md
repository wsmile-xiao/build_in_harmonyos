# burst 3.1.1 adaptation notes

## Build environment

- Build system: CMake 3.8.2+
- Language: C++14 header-only library; repository profiles compile as C++17
- Build date: 2026-09-12
- Package reference: `burst/3.1.1`
- Target profile: `ohos-aarch64` (OHOS 6.0, Clang 15, armv8)
- Status: CI #45099 executed all 724 upstream tests; signed-char compatibility fix pending rerun

## Source and dependencies

- Official source: `https://github.com/izvolov/burst/archive/refs/tags/v3.1.1.tar.gz`
- SHA-256: `ee58c7b98ca1709dd452b9ba46cb4c91fc0b2952edd020ed5bc2d600b3edeae7`
- Public dependency: `boost/1.90.0`
- Build-only test dependency: `doctest/2.5.2`

Both dependency recipes and OHOS armv8 binaries were resolved and downloaded from the configured `ohpcd` Conan registry before source adaptation began.

## Adaptation

Burst is fully header-only, so the recipe configures upstream CMake, executes the `check` target, and installs the public headers and `Burst::burst` CMake target. Benchmarks are disabled to avoid the optional compiled Boost.Program_options dependency.

The repository Boost package provides complete headers and models Boost.System as header-only, while Burst's historical test CMake still links `Boost::system`. The recipe therefore attaches a private CMakeDeps build module that defines `Boost::system` as an interface target backed by `Boost::boost`. No Burst source or test file is changed.

Because the repository profile uses C++17 and upstream treats every warning as an error, the recipe suppresses only the Clang deprecation diagnostic for Burst's pre-C++17 `std::result_of_t` usage. Apple Clang additionally receives its host-specific `u8` unevaluated-string warning suppression. Other upstream warnings remain fatal.

OHOS AArch64 compiles plain `char` as unsigned by default. Burst's unchanged `to_unsigned` doctest explicitly places plain `char` in its signed-integer template matrix and expects zero to map to 128. CI #45099 therefore ran the complete suite but reported `0 == 128` for that single specialization: 723/724 cases and 1035/1036 assertions passed. Following knowledge E419, the OHOS upstream-test build now uses `-fsigned-char`, preserving the upstream source and its intended signed-char test model without suppressing or deleting any case.

For OHOS, the recipe and consumer test use CMake's Linux platform model with processor `aarch64`, while retaining the real OHOS Conan profile and compiler. Burst is platform-neutral/POSIX-only, and this follows the repository's E092 pattern for runners whose CMake has no built-in OHOS platform module. Setting `CMAKE_SYSTEM_NAME` makes CMake classify the build as cross-compiling, so upstream's `COMMAND burst-unit-tests` remains a bare command. CI #43824 consequently linked the executable but failed with `/bin/sh: burst-unit-tests: inaccessible or not found`. The recipe now builds the exact `burst-unit-tests` target and executes its absolute path with the same doctest arguments as upstream `check`, avoiding global changes to CMake's cross-compiling state while preserving the complete suite.

## Validation

### Pre-adaptation upstream baseline

- Source files: 96 C++ test translation units
- Framework-reported cases: 724 passed, 0 failed, 0 skipped
- Framework-reported assertions: 1,036 passed, 0 failed

### Native Conan lifecycle

The complete Conan create flow passed on the available Apple arm64 host:

- generated `Boost::system` compatibility target loaded successfully;
- upstream test executable invoked by absolute path with the original `check` arguments: 724/724 cases and 1,036/1,036 assertions passed;
- package installed 185 Burst headers and its CMake config;
- consumer test built via `find_package(Burst CONFIG REQUIRED)` and `Burst::burst`;
- consumer result: four scenarios and six assertions passed.

### OHOS gate

The local `conan-verify --profile ohos-aarch64` run passed G0 and G1 but could not compile because `/data/service/hnp/bin/clang++` exists only on the OHOS repository runner. Remote CI #45099 confirmed that the compiler, Boost and doctest dependencies, CMake configuration, all 96 test translation units, final linking, and absolute-path test launch work on OHOS 6.0 armv8. It executed all 724 doctest cases; 723 passed and the sole failure was `to_unsigned<char>` because OHOS AArch64 defaults plain `char` to unsigned. The recipe now adds `-fsigned-char` only for the OHOS upstream-suite build; a new `/rebuild` must confirm 724/724 and the downstream package gates.

## Test counting basis

The canonical unit is a framework-reported logical test case. Doctest expands template cases, so its runtime count of 724 is authoritative over the 638 literal `TEST_CASE` macro occurrences. The consumer program adds four independent scenarios, for a planned adapted total of 728 cases and 1,042 assertions.

## Source modifications

None.
---

**编译结束**: 待远程 CI 复核
**最终状态**: failed
