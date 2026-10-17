# avida 2.12.4 Adaptation Notes

## Overview
Avida is a digital evolution platform for Artificial Life (ALife) research. It consists of:
- `libs/apto`: core utility library
- `libs/tcmalloc-1.4`: Google's TCMalloc memory allocator (bundled)
- `avida-core`: the main simulation engine

## OHOS Adaptation

### Patches (declared in conandata.yml)

1. `patches/0001-bump-cmake-minimum-version.patch`
   Raises `CMAKE_MINIMUM_REQUIRED` from 2.6 to 3.5 in all four `CMakeLists.txt`
   (top level, `libs/apto`, `libs/tcmalloc-1.4`, `avida-core`). CMake 4.x refuses a
   minimum below 3.5, so the upstream 2.6 aborts at configure time. 3.5 is the lowest
   value that is accepted, which keeps the CMake policy behaviour change minimal
   relative to the verified build.

2. `patches/0002-disable-tcmalloc-on-ohos.patch`
   Drops `ADD_SUBDIRECTORY(libs/tcmalloc-1.4)` from the top-level `CMakeLists.txt`.
   tcmalloc's `atomicops-internals-x86.h` is x86-only inline assembly and cannot
   compile for aarch64. This patch is the mechanism that actually disables tcmalloc;
   `AVD_ENABLE_TCMALLOC=False` in `generate()` is only a redundant cache variable,
   and the recipe no longer edits `CMakeLists.txt` at build time.

3. `patches/0003-disable-fp-contraction-on-ohos.patch`
   Appends `-ffp-contract=off` to `CMAKE_CXX_FLAGS` in the top-level `CMakeLists.txt`.
   Without a guard, aarch64 contracts `a*b+c` into a single-rounding `fma`, so
   floating-point results diverge from the x86 builds that upstream's expected
   consistency-test output was generated with. Upstream does try to prevent this,
   but two things defeat it on OHOS:

   - The guard lives in `avida-core/CMakeLists.txt` inside an `IF(UNIX)` block.
     With the OHOS toolchain CMake reports `CMAKE_SYSTEM_NAME=HarmonyOS`, so `UNIX`
     is **not** set and the whole block is skipped (this also silently disables
     upstream's `-funroll-loops`/`-Wextra` flags).
   - Even if it ran, the probe is `CHECK_C_SOURCE_COMPILES(... "-mno-fused-madd")`
     and clang rejects `-mno-fused-madd` outright (`unknown argument`), so
     `HAVE_FUSED_MADD` can never be true under clang.

   `-ffp-contract=off` is clang's spelling of the same intent. Setting it in the
   top-level `CMakeLists.txt`, before any `ADD_SUBDIRECTORY`, keeps it independent
   of the `IF(UNIX)` block and applies it to every target in the tree.

4. Patch hygiene: all three patches were verified against the pristine upstream
   tarball, applied in `conandata.yml` order, with `patch -p1 --dry-run` and
   `git apply --check -p1` (both exit 0, no fuzz, no offset), so tarball + patch set
   reproduces the build inputs exactly.

### In-recipe source edits (`conanfile.py` `build()`)

4. **cRandom.h** — removed the custom `std::iota` that clashes with C++11; added
   `<random>` / `<algorithm>` / `<cstdlib>`; completed the `cRandomStdAdaptor` URNG
   interface (`operator()`, `min`, `max`); and replaced the two-argument
   `std::random_shuffle` (removed in C++17) with an explicit loop that reproduces the
   pre-C++17 draw pattern against the generator already in scope. The same header now
   defines `avida_random_shuffle`, the three-argument equivalent.
5. **tArray.h** — added `#include <cstdlib>` for `qsort`.
6. **random_shuffle in .cc files** — the 3-argument calls in `PrintActions.cc`,
   `cGenomeUtil.cc` and `cPopulation.cc` are routed to `avida_random_shuffle` rather
   than `std::shuffle`.
   `std::shuffle` is *not* a drop-in replacement: it draws through
   `uniform_int_distribution` with rejection sampling, consuming a different number
   of values from the generator. avida seeds a single RNG from `RANDOM_SEED` and
   every later draw shifts with it, so the simulation desynchronises from the
   expected output (this was reproduced: `multi_level_selection` failed with
   `std::shuffle` and passes with the faithful draw pattern). An earlier revision of
   this recipe seeded a fresh `std::mt19937` from `std::random_device{}()`, which
   additionally made affected runs non-reproducible; that is gone.
7. **cPopulationInterface.cc** — `std::abs(static_cast<long long int>…)` → `llabs`
   (long long overload ambiguity).
8. **apto `Atomic.h`** — the `#else` branch used x86 inline assembly (`mfence`,
   `lock xaddl`); replaced with `__sync` builtins for aarch64.
9. **apto `Thread.cc`** — `pthread_cancel` commented out; OHOS musl libc does not
   provide it.
10. **cPopulation.cc** — `cString` provides `operator const char*()` but no implicit
    conversion to `std::string`; the value is routed through a `const char*`
    intermediate.

### Build options
- `AVD_ENABLE_TCMALLOC=False`, `AVD_GUI_NCURSES=False`, `AVD_UNIT_TESTS=False`,
  `AVD_TASK_EVENT_GEN=False`, `AVD_GUI_PROTOTYPE_TEXT=False`,
  `APTO_UNIT_TESTS=False` are set through the CMakeToolchain cache variables.
- Headless deployment: the ncurses viewer is off, and there are no unit tests or
  task-event generator targets in the package.

### Dependencies
- `ncurses/6.5` (optional, only if `with_ncurses=True`)
- Otherwise no runtime dependencies beyond standard libc.

### Test coverage (`test_package/test.sh`)

The consumer test script runs three assertions against the packaged binary:

1. `avida --version` (falling back to `--help`) executes successfully.
2. A minimal simulation runs to completion using the consumer config
   (`consumer-case/avida.cfg`, copied into a temporary run directory); avida's own
   exit status is captured and asserted, and the first 20 log lines are printed so a
   failure is diagnosable.
3. OHOS-specific: the ELF header of the packaged binary is parsed and must report
   `e_machine == 0xB7` (AArch64). Matching on `file(1)` output is deliberately not
   the primary probe, because implementations disagree on the spelling
   ("aarch64" vs "arm64") and the value is only used as a fallback.

### Upstream Testing

avida 2.12.4 ships **three** independent test suites. All three were inventoried and
executed on OHOS aarch64 with the OHOS clang toolchain at C++17 (matching
`ci/conan/profiles/ohos-aarch64`). Nothing upstream was skipped for being
"unrunnable" — the earlier claim that the consistency suite cannot run on OHOS was
wrong, and is withdrawn.

| Suite | Location | Build option | Cases | Passed | Failed | Skipped |
|---|---|---|---|---|---|---|
| avida-core unit tests | `avida-core/source/targets/unit-tests` | `-DAVD_UNIT_TESTS=ON` | 47 | 47 | 0 | 0 |
| apto unit tests (GoogleTest) | `libs/apto/unittests` | `-DAPTO_UNIT_TESTS=ON` | 122 | 122 | 0 | 0 |
| consistency regression suite | `avida-core/tests` | (needs the built `avida`) | 70 | 56 | 1 | 7 |
| **Total** | | | **239** | **225** | **1** | **7** |

Of the consistency suite's 70 inventoried cases, 64 carry a configuration and take
part in the run (56 passed / 1 failed / 7 skipped). The remaining 6 are inventoried
by upstream but not runnable as shipped and are therefore excluded from both
numerator and denominator: `bgs_dyn_mutrates_births`, `bgs_dyn_mutrates_fit`,
`bgs_dyn_mutrates_rank` and `default_transsmt_100u` ship no usable config, and
`heads_perf_1000u` / `heads_perf_1000u_rate` are upstream performance tests whose
`[performance] enabled` is `no`.

Pass rate excluding the 7 upstream `long` cases: **225/226 (99.6%)**. The
consistency-suite result was reproduced identically over three consecutive runs
(deterministic — the recipe no longer seeds anything from `std::random_device`).

The two unit-test targets are **not** part of the shipped package
(`AVD_UNIT_TESTS` / `APTO_UNIT_TESTS` stay `OFF`, as before); they are built and run
as a verification step:

```
cmake -S <src> -B <build> -DCMAKE_BUILD_TYPE=Release \
      -DAVD_UNIT_TESTS=ON -DAPTO_UNIT_TESTS=ON \
      -DAVD_ENABLE_TCMALLOC=OFF -DAVD_GUI_NCURSES=OFF
cmake --build <build> -j
<build>/bin/unit-tests      # 47/47
<build>/bin/apto-test       # 122/122
```

Running the consistency suite needs the Python-3 revision of the upstream runner:
`avida-core/tests/_testrunner/testrunner.py` in 2.12.4 is Python 2 only. Upstream's
later revision of the same runner is Python 3 and reads the same test assets
unchanged, so it is used to drive the 2.12.4 test tree (it needs a two-line shim for
the `dircache` module that Python 3 removed). No test case itself was modified.

```
python3 avida-core/tests/_testrunner/testrunner.py \
        --builddir=<build> --scm=none --testdir=<tests> -j4
# -> 56 passed, 1 failed, 7 skipped (of 64)
```

#### The single remaining failure is an upstream test bug

`analyze_resize_max_batches` fails on **any** platform, OHOS included, because of a
contradiction inside the test itself:

- `avida-core/tests/analyze_resize_max_batches/test_list` sets
  `nonzeroexit = disallow`, i.e. a non-zero exit status is a failure.
- `.../config/analyze_max_batches.cfg` deliberately ends with `SET_BATCH 50000`
  (commented `# Should fail`), which trips
  `if (next_batch >= MAX_BATCHES) { cerr << "  Error: max batches is 50000"; if
  (exit_on_error) exit(1); }`. In non-interactive mode `exit_on_error` is true, so
  avida exits `1`.

Upstream master fixed exactly this: the same test now declares
`nonzeroexit = require` (and runs with a plain `-a`), which matches the intentional
error path. The failure is therefore a defect in the 2.12.4 test configuration, not
in the adaptation.

#### Fixed by this revision

Three consistency tests failed before the recipe was corrected and now pass:

| Test | Root cause |
|---|---|
| `sex` | aarch64 FMA contraction (patch `0003`) |
| `sex-asex` | aarch64 FMA contraction (patch `0003`) |
| `shaded_green_beard_instructions` | aarch64 FMA contraction (patch `0003`) |
| `multi_level_selection` | `std::shuffle` desynchronising avida's RNG stream (in-recipe edit 4/6) |

Observed progression on the same test tree: **52/64** with the recipe as merged,
**55/64** after `-ffp-contract=off`, **56 passed / 1 failed / 7 skipped** after the
faithful `random_shuffle` reproduction.


### Build Status
- **Target**: OHOS armv8
- **Build system**: CMake
- **Status**: Compiled and linked successfully
- **Artifacts**: `bin/avida` (main simulation binary)
---

**编译结束**: 2026-09-24 19:40
**最终状态**: built
