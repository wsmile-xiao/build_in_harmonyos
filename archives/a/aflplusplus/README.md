# AFLplusplus

AFL++ (American Fuzzy Lop Plus Plus) is a fast instrumented fuzzer with
many enhancements over the original AFL: better instrumentation, faster
mutations, additional sanitizers, custom mutator API, and more.

- **Versions**: 4.33c, 4.33c.1, 4.34c-r0
- **Homepage**: https://github.com/AFLplusplus/AFLplusplus
- **License**: Apache-2.0
- **Build System**: Makefile (GNUmakefile)
- **Type**: CLI tool (fuzzer)

## OHOS Build Notes

Core fuzzing tools are built:
- `afl-fuzz` — main fuzzer
- `afl-showmap` — coverage map tool
- `afl-tmin` — test case minimizer
- `afl-gotcpu` — CPU affinity checker
- `afl-analyze` — input analysis

LLVM-based instrumentation (`afl-cc`, `afl-clang-fast`, 10 LLVM pass plugins,
`afl-compiler-rt.o`) is **built** using the LLVM 15.0.4 shipped in the OHOS
SDK. GCC plugin / LTO / IJON modes are not built (no gcc-plugin-dev / LLD).
