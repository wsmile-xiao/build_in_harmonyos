# GROMACS 2026.3 HarmonyOS PC Notes

## Build Scope

- CPU-only AArch64 build using `GMX_SIMD=ARM_NEON_ASIMD`.
- Mixed precision is retained with `GMX_DOUBLE=OFF`.
- Built-in thread-MPI is enabled; external MPI and OpenMP are disabled.
- GPU, GMXAPI, HDF5, NNPot, PLUMED, Python packaging, generated help, and
  manual builds are disabled.
- Ninja is used with at most 20 parallel jobs.

## FFTW Dependency Bridge

GROMACS uses its own `FindFFTW.cmake` and does not consume the Conan CMake
target exported by `fftw3f`. The recipe therefore validates the dependency
package layout and passes its exact `include/fftw3.h` and `lib/libfftw3f`
paths as `FFTWF_INCLUDE_DIR` and `FFTWF_LIBRARY`.

## Thread-MPI Portability

HarmonyOS does not declare the POSIX `pthread_cancel` API. The first target
build reached `src/external/thread_mpi/src/pthreads.cpp` and failed at that
single undeclared call after CMake configuration and FFTW discovery had
completed. The OHOS branch now follows thread-MPI's existing unsupported-
cancellation contract for Native Client and returns `ENOSYS`; it never reports
cancellation success. The normal POSIX branch still calls `pthread_cancel`.

The target failure is preserved under
`/storage/Users/currentUser/.ohpcd-w3/gromacs-2026.3-20260730T0543`.
`conan-create.log` has SHA256
`73861d464c02d12963431d4893470fec56dd6981cf10afb7d24304ce9eea72a6`.

An isolated target compile replay used the failed build's generated headers,
include paths, flags, and compiler. The unmodified source failed with
`RC=1`; the OHOS-adapted source compiled with `RC=0` and an empty diagnostic
log. The resulting object has SHA256
`3b79f9f2b89d9e93bd447bc568749af7e59f7530abed31456d6a193e386b69d9`.

## Tests

`BUILD_TESTING=ON` and `GMX_BUILD_UNITTESTS=ON` preserve the complete CTest
suite registered by this CPU-only configuration. An early target run completed
the default GROMACS build and registered 86 CTest entries, but all 86 were
reported as `Not Run` in 0.09 seconds because the corresponding test
executables had not been built. Upstream excludes those executables from the
default build and provides the explicit `tests` target for that purpose. The
recipe therefore builds `tests` before invoking CTest.

The second target failure is preserved under
`/storage/Users/currentUser/.ohpcd-w3/gromacs-2026.3-20260730T061532`.

A later r7 run built and launched the complete suite. It passed 79 of the 86
registered CTest entries; the remaining seven mdrun groups each exhausted the
600-second per-test timeout. The failure was not a generic thread-MPI defect:
the corresponding unit and MPI infrastructure tests passed, while the direct
3D FFTW planner still selected `FFTW_MEASURE` even though the generated
`GMX_DISABLE_FFTW_MEASURE` macro was `1`.

Patch 0005 propagates the configured policy to that final direct planner
selection. The fresh r8 run then passed all 86 registered CTest entries in
29.70 seconds. CTest-level platform exclusions within the CPU-only build, such
as GPU-only parameterizations, remain upstream-declared skips inside passing
test executables; no registered CTest entry was filtered, failed, timed out, or
left unexecuted.

The Conan consumer runs the packaged `gmx` binary, verifies its version, uses
`gmx editconf` to convert a two-atom PDB file, and validates the generated GRO
atom count and atom names. The same r8 `conan create` passed the one independent
consumer flow and all 10 explicit assertions.

## FFTW Planning Policy

`GMX_DISABLE_FFTW_MEASURE=ON` is bound through the CMake toolchain. The
generated target `config.h` contains `#define GMX_DISABLE_FFTW_MEASURE 1`, and
the patched `fft5d.cpp` maps either `FFT5D_NOMEASURE` or that generated macro
to `FFTW_ESTIMATE`. This keeps transform and simulation assertions intact
while preventing every short-lived PME process from repeating exhaustive
planning.

## Final Target Evidence

- Run: `/storage/Users/currentUser/.ohpcd-w4/gromacs-2026.3-20260730T1444-r8`
- Result: `RC=0`, from `2026-07-30T14:44:52+08:00` to
  `2026-07-30T14:53:48+08:00`
- CTest: 86/86 passed, 0 failed, 29.70 seconds real time
- Consumer: 1/1 independent flow passed, with 10/10 assertions
- `conan-create.log` SHA256:
  `e7f92b09ac24fc7b9244a73ebb9d6265f41a34577efea378a7ac96a01aab39be`
- `LastTest.log` SHA256:
  `9f668c668e63ad54a469a142da37bff319a7adf45f39660452234f5e17d54708`
- `result.env` SHA256:
  `ba4fa06f7783888f2fb165c13d2180e545b6724370b83693a515465e7a50a8b4`
- Generated `config.h` SHA256:
  `b04c9c41af947c605ed33f6a1eaeda625fb74139d88fa570e9d5941682d8a398`
- Patched `fft5d.cpp` SHA256:
  `c5fcc3492d8a116fd5611fa807e8d2ca1ed7c9741603e18a3bcf4a81f0287c00`

## Local Preflight Evidence

- `v2026.3` resolves to upstream commit
  `121090014570a53a17ea391bcddae45e5ea05eb4`.
- The downloaded official archive matches SHA256
  `6e205f8fc072f0112dc72f6349b729c6921e1ddb7231928c03281f950a86d42f`.
- `conan download fftw3f/3.3.9 -r=ohpcd --only-recipe` completed with recipe
  revision `3a7ddd30398dddb9a57452eac3358959`.
- Patch 0001 has SHA256
  `a4556d9ce75f354c3708fe5622f72f341e951e7f9aef891f593220e05b59bf9b`
  and applies to the pristine archive with `patch --dry-run -p1` from the
  declared `base_path`.
- Patch 0005 has SHA256
  `43189749fb22cced6ed56dccd0a56663b681f2939fb74367f2a2bec3dc55f966`
  and the complete five-patch sequence applies in `conandata.yml` order.
- All three Python inputs pass AST parsing; `conandata.yml`, `commands.json`,
  and `test_package/MANIFEST.yml` pass structured parsing; `conan inspect`
  identifies `gromacs/2026.3` as an application package.

The fresh target build and test run is complete, so the archive status is
`built`. It is not `published` until the merged release pipeline uploads the
package.
