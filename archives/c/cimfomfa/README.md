# cimfomfa

cimfomfa is a C utility library used by the MCL graph-clustering software and
the zoem macro language. Its installed artifact is named `libtingea` and
provides memory, string, I/O, collection, hashing, heap, parsing, and random
number utilities.

## HarmonyOS adaptation

- Recreates the Autotools generated files omitted from the official Git tag.
- Uses the published `automake/1.18` build tool package on minimal CI workers.
- Builds the upstream static `libtingea.a` archive without source patches.
- Installs the upstream `tingea/*.h` public header set.
- Compiles all 16 upstream trumpet programs and executes nine representatives.
- Verifies installed-package string and binary-search APIs in `test_package`.

## References

- https://github.com/micans/cimfomfa
- https://github.com/micans/mcl
