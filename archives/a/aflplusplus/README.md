# AFLplusplus

AFL++ (American Fuzzy Lop Plus Plus) is a fast instrumented fuzzer with
many enhancements over the original AFL: better instrumentation, faster
mutations, additional sanitizers, custom mutator API, and more.

- **Version**: 4.33c
- **Homepage**: https://github.com/AFLplusplus/AFLplusplus
- **License**: Apache-2.0
- **Build System**: Makefile (GNUmakefile)
- **Type**: CLI tool (fuzzer)

## OHOS Build Notes

Only the core fuzzing tools are built:
- `afl-fuzz` — main fuzzer
- `afl-showmap` — coverage map tool
- `afl-tmin` — test case minimizer
- `afl-gotcpu` — CPU affinity checker
- `afl-analyze` — input analysis

LLVM-based instrumentation (`afl-cc`, `afl-clang`, `SanitizerCoverage*.so`)
and GCC plugin are **not built** — they require LLVM/GCC development packages
which are not available in the OHOS CI environment.
