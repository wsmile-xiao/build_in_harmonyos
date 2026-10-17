# Validation report

- Initial preflight: 2026-08-17, Windows host
- Device validation: 2026-08-21, HarmonyOS/aarch64
- Package: `avr-libc/2.2.1`

## Local preflight

- Branch/worktree isolation confirmed.
- Official tag metadata and authoritative source mirror checked.
- Source archive downloaded, SHA256 verified and extracted successfully.
- Autotools/bootstrap, AVR GCC/Binutils dependency and multilib layout analyzed.
- Upstream test inventory counted: 462 sources in 17 categories (406 C, 53 C++,
  and 3 assembly sources).
- Python AST parsing passed for both Conan recipe files.
- YAML parsing passed for conandata, manifest and test manifest.
- `conan inspect`, `conan source` and `conan export` passed with the OHOS-adapted
  Conan 2.29.1 client.
- The initial dependency graph stopped at the two then-unpublished AVR tools, as
  expected from W0; those tools were subsequently adapted in #2244 and #2245.

## True-device Shadow CI

- Full recursive AVR device/multilib build: 470/470 directories completed.
- Supplemental true-device run r23: all 409 C/assembly sources passed for
  AT90S8515 (409/409, 100%; stderr was empty).
- Final standard CI run r25: 409/409 upstream compile/link sources passed and the
  Conan consumer passed (1/1).
- Executed checks: 410/410 passed (100%).
- Package and gate result: 1 package succeeded, 0 failed.
- Gates: G0 pass, L0 pass, L1 pass, L2 skip, L4 pass, L5 pass.
- Outer run: `codex-avr-libc-shadow-ci-r25-2240-resume-cache-20260821-200845-55576`.
- Shadow workspace: `codex-avr-libc-shadow-ci-r24-2240-full-409-20260821-190344-19933`.
- Shadow commit: `6b817115bf6e48d28dc980437357bdf034aff66b`.

The cold-cache r24 run completed the full build and 409/409 tests, then reached the
3600-second CI limit during `make install` because the source download consumed
about 12 minutes. Run r25 reused only the verified source cache and repeated the
full build, tests, install, package and consumer workflow; it ended with exit code 0.

L2 is non-blocking because the packaged documentation helper `avr-man` does not
accept `--version` or `--help`. It is not the package's primary executable surface.
The AVR sysroot was validated through upstream sources and the consuming package.

## Coverage boundary

The compile/link coverage is 409/462 sources (88.53%) and 409/409 eligible
C/assembly sources passed (100%). The remaining 53 C++ sources are blocked because
the independently adapted stage-1 `avr-gcc-bootstrap` package contains neither
`avr-g++` nor `cc1plus`; adding a full C++ compiler belongs in a separate dependency
adaptation. AVR runtime execution was not run because neither `avrtest` nor
`simulavr` is currently packaged. The generated AVR ELF cannot execute natively on
the OHOS/aarch64 host.

See `shadow-ci.md` for the run history and detailed evidence.
