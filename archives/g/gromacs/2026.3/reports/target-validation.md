# GROMACS 2026.3 OHOS AArch64 validation

## Result

- Conan reference: `gromacs/2026.3`
- Target run: `gromacs-2026.3-20260730T1444-r8`
- Terminal state: `RC=0`, phase `conan-create`
- Wall interval: `2026-07-30T14:44:52+08:00` to
  `2026-07-30T14:53:48+08:00`
- Total wall time: 8 minutes 56 seconds
- Registered upstream CTest entries: 86/86 passed
- CTest real time: 29.70 seconds
- Packaged command consumer: 1/1 independent flow passed, with 10/10 assertions

The run used the five patches declared in `conandata.yml`, the published
`fftw3f/3.3.9` package, and a fresh Conan home. It did not filter registered
CTest entries. GPU-only parameterizations remain upstream-declared skips
inside passing CPU-only test executables.

## Planner evidence

The generated target `config.h` contains:

```c
#define GMX_DISABLE_FFTW_MEASURE 1
```

The applied `fft5d.cpp` direct 3D planner contains:

```c++
fftwflags |= ((flags & FFT5D_NOMEASURE) || GMX_DISABLE_FFTW_MEASURE)
                     ? FFTW_ESTIMATE
                     : FFTW_MEASURE;
```

This closes the r7 gap where the project-level no-measure option reached the
primary FFT wrapper but not the direct multidimensional planner.

## Frozen evidence

| Artifact | SHA256 |
|---|---|
| `conan-create.log` | `e7f92b09ac24fc7b9244a73ebb9d6265f41a34577efea378a7ac96a01aab39be` |
| `LastTest.log` | `9f668c668e63ad54a469a142da37bff319a7adf45f39660452234f5e17d54708` |
| `result.env` | `ba4fa06f7783888f2fb165c13d2180e545b6724370b83693a515465e7a50a8b4` |
| generated `config.h` | `b04c9c41af947c605ed33f6a1eaeda625fb74139d88fa570e9d5941682d8a398` |
| patched `fft5d.cpp` | `c5fcc3492d8a116fd5611fa807e8d2ca1ed7c9741603e18a3bcf4a81f0287c00` |
| patch 0005 | `43189749fb22cced6ed56dccd0a56663b681f2939fb74367f2a2bec3dc55f966` |

The local evidence copies are stored outside the repository under
`E:\HarmonyPC\validation`.
