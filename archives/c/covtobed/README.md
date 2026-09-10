# covtobed

covtobed is a C++ command-line tool that converts coverage from sorted BAM
alignment files into BED tracks.

## Features

- Reads one or more BAM files or a BAM stream.
- Emits coverage intervals in BED or counts format.
- Supports physical and strand-specific coverage.
- Filters by mapping quality, coverage, contig length, and alignment validity.

## HarmonyOS adaptation

- Compiles the two upstream C++ translation units directly because release
  1.3.5 does not ship a Makefile, CMake project, or configure script.
- Resolves the published `bamtools/2.5.3` and `zlib/1.3.1.1` packages through
  Conan rather than using hard-coded host paths.
- Runs the upstream `test/test.sh` integration suite with its official BAM
  fixtures during the package build.

## Dependencies

- `bamtools/2.5.3`
- `zlib/1.3.1.1`
- `perl/5.42.2` for the final upstream test scenario

## References

- https://github.com/telatin/covtobed
- https://github.com/telatin/covtobed/wiki
