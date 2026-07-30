# libxsmm 1.17

## OpenHarmony adaptation

LIBXSMM 1.17 defaults to an Intel-only JIT implementation. The OpenHarmony
armv8 package uses the upstream-documented `PLATFORM=1` fallback configuration,
which sets `JIT=0`. It also uses `BLAS=0` and disables the optional Fortran
interface, so this recipe has no package dependencies.

The upstream build assumes a writable `/tmp`, GNU `xargs -I`, and Bash alias
handling. The portability patch uses `TMPDIR`, a Toybox-compatible `xargs`
invocation, and Bash for the generated build-state script.

On armv8, the same patch disables the x86-only RDTSC timer macro. LIBXSMM then
uses its existing `clock_gettime(CLOCK_MONOTONIC)` timer fallback.

## Test coverage

The recipe executes the upstream `make tests` target using the same fallback
configuration. The consumer test links the packaged static archives, calls the
library initialization APIs, checks the reported target name, and verifies a
library allocation round trip.
