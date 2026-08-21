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
- Supplemental true-device compile/link run r23: all 409 C/assembly sources
  passed for AT90S8515 (409/409, 100%; stderr was empty).
- Conan consumer compile/link test: 1/1 passed.
- Package and gate result: 1 package succeeded, 0 failed.
- Gates: G0 pass, L0 pass, L1 pass, L2 skip, L4 pass, L5 pass.
- Shadow run: `codex-avr-libc-shadow-ci-r20-2240-requeued-20260821-160012-62802`.
- Shadow commit: `55eacfea2a4f0f547f6778b093cfba469024858e`.

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
