# adapterremoval

AdapterRemoval searches for and removes adapter sequences from high-throughput
sequencing reads.

## Version

- 2.3.4

## Build notes

The Conan recipe builds the upstream Makefile project against `zlib/1.3.2` and
`bzip2/1.0.8`, installs the `AdapterRemoval` CLI, and runs upstream unit tests
when the target binary can be executed.
