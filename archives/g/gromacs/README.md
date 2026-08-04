# GROMACS

GROMACS is a high-performance molecular dynamics suite with the `gmx`
command-line frontend.

## Features

- Molecular dynamics simulation and trajectory analysis
- CPU SIMD kernels and thread-MPI parallel execution
- FFTW-backed mixed-precision transforms

## HarmonyOS PC Adaptation

The HarmonyOS PC package is a CPU-only AArch64 build. It uses ARM NEON ASIMD,
thread-MPI, and the published single-precision `fftw3f/3.3.9` package. GPU,
external MPI, OpenMP, Python API, HDF5, NNPot, and PLUMED integrations are
disabled in the baseline package. The target build disables exhaustive FFTW
planning for short-lived processes, including GROMACS' direct 3D planner, and
uses the upstream fallback when the target `open_memstream` close/flush
contract is unavailable.

## Validation

- Fresh OHOS AArch64 `conan create`: passed
- Registered upstream CTest entries: 86/86 in 29.70 seconds
- Packaged `gmx --version` and `gmx editconf` consumer: 1/1 independent flow,
  10/10 assertions
- Package state: `built` (not yet published)

## Dependencies

- `fftw3f/3.3.9`

## Upstream

- Homepage: https://www.gromacs.org/
- Source: https://gitlab.com/gromacs/gromacs
