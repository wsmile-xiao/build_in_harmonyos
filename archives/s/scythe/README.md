# Scythe

Scythe is a Bayesian adapter trimmer that removes 3-prime contaminants from FASTQ reads while incorporating base quality information.

## OHOS adaptation

The package builds the upstream `scythe` executable with the Conan `zlib/1.3.2` dependency. The upstream `make test` target is malformed, so the recipe builds and runs the same two assertions in `src/tests/tests.c` directly. The consumer test also runs the executable on a gzip-compressed FASTQ file to verify the OHOS binary and its zlib-backed input path.

## Dependencies

- `zlib/1.3.2` at build time

## References

- [Upstream repository](https://github.com/vsbuffalo/scythe)
