# isl25 0.25 OpenHarmony Adaptation

- Uses the official isl 0.25 source archive.
- Builds against the published `gmp/6.3.0` Conan dependency.
- Runs the upstream `make check` suite when the build machine can execute target binaries.
- The consumer test creates an ISL context and verifies integer-value API behavior.
