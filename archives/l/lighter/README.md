# lighter

Lighter is a k-mer-spectrum based tool for correcting errors in, and trimming
adapters from, high-throughput sequencing reads. It reads FASTA/FASTQ, plain or
gzipped, and writes corrected records as ``<name>.cor.<ext>``.

## Version

- 1.1.3

## Build notes

The Conan recipe builds the upstream bare-Makefile project against
`zlib/1.3.2` (used by `File.h`/`Reads.h` for `gzopen`/`gzread`), overrides the
hard-coded `CXX = g++` with the Conan-provided compiler, and installs the single
`lighter` CLI by hand because upstream defines no install target.
