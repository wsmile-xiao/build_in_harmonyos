# opari

`opari` (OPARI: OpenMP Pragma And Region Instrumentor) is a source-to-source
instrumentation tool for OpenMP programs: it rewrites `#pragma omp` constructs
into explicit calls to the POMP measurement runtime, so that parallel regions,
loops and barriers can be traced at run time.

The package ships two artifacts:

- `bin/opari` — the C++ source-to-source translator (CLI tool).
- `lib/libpomp.a` — the C POMP measurement runtime, linked into the
  instrumented executable.

Homepage: https://www.fz-juelich.de/ias/jsc/opari/

## Versions

| Version | Status |
| --- | --- |
| 1.1 | built |

## Usage on OpenHarmony (aarch64)

```sh
opari foo.c                      # -> foo.mod.c + foo.c.opari.inc
clang -fopenmp -I<pkg>/include -c foo.mod.c -o foo.o
clang -fopenmp foo.o pomp_rt.o -o foo -L<pkg>/lib -lpomp -lomp
./foo                            # POMP region events on stderr
```

`pomp_rt.c` must define `POMP_MAX_ID` and `pomp_rd_table[]`, which
`pomp_lib.h` declares `extern`. See `1.1/test_package/pomp_rt.c`.

Fortran support (`pomp_fwrapper.c`) is not built: the OHOS SDK ships no
gfortran, so there is no Fortran consumer on this platform.
