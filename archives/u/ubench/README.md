# ubench

ubench (Unix Benchmark Utility) by Sergei Viznyuk gives a single CPU score
(integer + floating-point work) and a memory score (malloc + memcpy work) for
a Unix system, each run for 3 minutes with about two worker processes per CPU;
`-s` runs a single calibrated pass instead.

- Upstream: https://www.ibiblio.org/pub/Linux/system/benchmark/ (ubench.lsm)
- Source: https://www.ibiblio.org/pub/Linux/system/benchmark/ubench-0.32.tar.gz
- License: GPL-2.0-or-later (source file headers)
- Usage: `ubench [-cmhs]` — `-c` CPU, `-m` memory, `-s` single pass
