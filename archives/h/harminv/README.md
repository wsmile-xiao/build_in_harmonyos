# harminv

**harminv** — harmonic inversion of time series data.

A library and command-line tool for extracting the frequencies, decay
rates, amplitudes and phases of exponentially-decaying sinusoids from a
signal, using the filter-diagonalization method (FDM). Typical use:
analyzing time-domain simulation output (e.g. FDTD electromagnetics).

| Field | Value |
|---|---|
| Upstream | https://github.com/NanoComp/harminv |
| Version | 1.4.3 |
| License | GPL-2.0-or-later (MIT-like portions, see COPYRIGHT) |
| Language | C |
| Build system | direct compile (upstream autotools skipped) |

## Dependencies

- `lapack/3.12.1` — reference BLAS + LAPACK + FortranRuntime/FortranDecimal
  (statically linked into `libharminv.a` and the `harminv` CLI)

## OHOS Adaptation

Upstream `configure` unconditionally probes for a Fortran compiler
(`AC_F77_*`) and auto-detects BLAS, neither of which is feasible on
HarmonyOS PC (no gfortran; flang-ohos unavailable in the build
environment). The recipe therefore skips autotools entirely:

- `build()` compiles `harminv.c` / `harminv-main.c` directly with clang,
  generating `config.h` with `VERSION` and the F77 name-mangling macros
  (`F77_FUNC` = lowercase + trailing underscore, matching the reference
  LAPACK ABI: `dgemm_`, `zgeev_`, ...)
- links against the `lapack/3.12.1` package (static)
- `ar` archives `libharminv.a`; `bin/harminv` CLI is a PIE executable
  whose DT_NEEDED closure resolves to `libc.so` only

No source patches needed.

## Test Coverage

- Upstream: `sines-test.sh` end-to-end pipeline (1/1 PASS, see
  `1.4.3/reports/upstream-test.log`)
- test_package: consumer API test (frequency recovery) + OHOS-specific
  non-assertion DT_NEEDED shared-library closure check (rule12)
