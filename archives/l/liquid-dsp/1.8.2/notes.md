# liquid-dsp 1.8.2 适配笔记

## 任务身份

- Contributor task: `liquid-dsp/1.8.2`
- Branch: `feat/liquid-dsp-1.8.2`
- Official source: `https://github.com/jgaeddert/liquid-dsp/archive/refs/tags/v1.8.2.tar.gz`
- Source SHA-256: `A0ADBC3EC5630D620A55351285573F59948153A14C703FB64B4AD58989BD6E2F`
- Activity: `开源鸿蒙PC专项积分赛-依赖`

## W0 source review

The upstream CMake configuration makes FFTW optional and links the core library
against the platform C/math libraries. The recipe disables `FIND_FFTW`, examples,
benchmarks, and shared output, so the declared Conan dependency closure is empty.
The upstream build enables the aggregate `xautotest` target and CTest.

## Adaptation change

`0001-cmakelists-static-config.patch` keeps the logical package name `liquid`
when only the static library is built. This preserves the generated
`liquidConfig.cmake` and `liquidTargets.cmake` identity while retaining the
`liquid::liquid-static` consumer target.

The OHOS cross configuration also disables `FIND_SIMD` and `ENABLE_SIMD`.
Upstream implements its SIMD feature checks with `try_run()`, which cannot
execute an AArch64 OHOS probe on the Windows build host. Guessing cached probe
exit codes would make the target feature selection unauditable; the portable
implementation remains functional and is covered by the target consumer.

## Verification status

- Python recipe and test recipe syntax: PASS (`py_compile`).
- Fresh WSL install prefix `install-wsl-r2`: PASS; generated
  `lib/cmake/liquid/liquidConfig.cmake` and target `liquid::liquid-static`.
- Upstream CTest aggregate: PASS, `1/1` (`autotest`, 121.28 seconds). The
  declared upstream inventory remains separate: 1341 tests and 716520
  assertions.
- Consumer CMake test from the fresh prefix: PASS, `1/1`; checks
  `liquid_nchoosek`, `liquid_version`, and `windowf`.
- A Windows-host Conan `create` was attempted once with the default Windows
  profile and failed before package completion because the POSIX source path
  uses `timespec_get`/`TIME_UTC` and `strsep`. This is a host-profile mismatch,
  not OHOS target evidence; it is retained as a boundary record and is not
  retried with a different identity.
- Knowledge draft pair: `knowledge/drafts/E603-draft-7C2A.{kv,md}`.
- Target-device W3 evidence is stored outside the candidate tree and must bind
  the exact final staged tree before PR. Historical r001-r003 records are not
  reused after recipe or metadata changes.
- Platform CI, AI Review, Pre-PR, and提审 remain pending. No platform or
  submission PASS is claimed until those gates produce current evidence bound
  to this tree.
