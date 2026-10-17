# YAHA

YAHA (Yet Another High-throughput Aligner) is a command-line sequence read aligner for mapping reads to a reference genome.

## Features

- Builds an index from a reference sequence.
- Aligns reads supplied in FASTA or FASTQ format.
- Emits SAM alignments and supports multithreaded alignment.

## HarmonyOS adaptation

- The Conan package builds for HarmonyOS PC aarch64 with the repository's OHOS Clang toolchain.
- The upstream Makefile sets `CC` and `CPP` internally, so the recipe passes the selected `clang` and `clang++` executables as command-line Make variables.
- The packaged binary was run on HarmonyOS 6.0 on aarch64. Its test creates an index and checks real SAM output for FASTA and FASTQ reads.
- The source patch removes duplicate default arguments from a C++ function definition, retaining the defaults on its forward declaration.

## Dependencies

There are no Conan build or runtime dependencies. The executable uses the target system's C/C++ runtime and pthread support.

## References

- Upstream repository: <https://github.com/GregoryFaust/yaha>
- Upstream license: MIT
