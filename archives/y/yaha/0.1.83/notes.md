# yaha 0.1.83

## Source and platform

- Upstream: https://github.com/GregoryFaust/yaha, tag `v0.1.83`.
- The source README documents Linux support. The package adds a HarmonyOS PC aarch64 build using the repository's OHOS clang toolchain.
- The upstream Makefile sets `CC := gcc` and `CPP := g++`; Conan passes compiler executable overrides on the `make` command line so the aarch64 cross compilers are selected. The existing `-pthread` link option is retained.
- No Conan build or runtime dependencies are required.

## Commands

- Build a reference index: `yaha -g reference.fa`.
- Align FASTA or FASTQ reads: `yaha -x <index> -q <reads.fa|reads.fq> -osh <output.sam> -t <threads>`.
- The packaged executable is `bin/yaha`; `yaha -xh` prints the upstream command help.

## Test inventory and coverage

The v0.1.83 source tree has no `tests/` directory, standalone automated test files, CTest registration, or pytest registration. The upstream `testdata/README.txt` describes example input data and does not define a test runner. The upstream test census and attempted entrypoint run are recorded below; upstream automated test count: **0**.

| Census item | Result | Evidence |
|---|---:|---|
| `tests/` directories | 0 | Clean extracted v0.1.83 source has only `src/` and `testdata/` directories. |
| Standalone registered test files | 0 | No test harness or test source files are present; `testdata/README.txt` describes example datasets. |
| CTest / pytest registrations | 0 / 0 | No CMake/CTest project or pytest suite is present in the source tree. |
| Upstream `make check` | Not available | Ran on the clean source on HarmonyOS: `make: *** No rule to make target 'check'. Stop.` |

The upstream test command could not be executed because the Makefile defines no `check` target. This is a source-level absence, not an environment limitation.

The consumer test creates an index from a small reference, aligns an exactly matching 50-base read from both FASTA and FASTQ input with two threads, and checks the resulting SAM QNAME, FLAG, reference name, position, and CIGAR. The same workflow is run by the Conan test package and on a HarmonyOS 6 aarch64 device under HNP Bash; it exercises the packaged target executable and verifies actual alignment output.

## Source fix found during HarmonyOS build

Clang 15 rejects the upstream `src/SW.cpp` template because `findAffineGapScore` repeats its default arguments on the function definition after declaring them on the forward declaration. The package patch removes the repeated defaults from the definition and retains them on the declaration, preserving the existing call behavior. Conan applies this source patch before compiling.
