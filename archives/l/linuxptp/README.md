# linuxptp

Linux implementation of the Precision Time Protocol (PTP) according to IEEE standard 1588.
Ships the user-space tools `ptp4l`, `phc2sys`, `pmc`, `ts2phc`, `timemaster`, `hwstamp_ctl`,
`phc_ctl`, `nsm` and `tz2alt`.

## Homepage
https://linuxptp.sourceforge.net/

## License
GPL-2.0-or-later

## Build System
Raw GNU Makefile (not autotools): `make` / `make install` / `make clean`.

## Dependencies
- No third-party libraries. Links only against the system C library plus `-lm -lrt -pthread`.

## OHOS Adaptation
- The Makefile hardcodes `CC = $(CROSS_COMPILE)gcc`; OHOS has no `gcc`, so `clang` is injected
  through the Conan toolchain (`tools.build:compiler_executables`) instead of shell variables.
- `KBUILD_OUTPUT` must point at the OHOS sysroot: upstream `incdefs.sh` probes
  `${KBUILD_OUTPUT}/usr/include` for the kernel UAPI headers (`net_tstamp.h`, `ptp_clock.h`).
  Without it the probe greps the host `/usr/include`, fails, and `missing.h` redefines
  `HWTSTAMP_TX_ONESTEP_*` (R51 evidence: `missing.h` conflict on aarch64).
- The OHOS wrapped compiler predefines `__MUSL__` (a bare `clang` does not). `<sys/socket.h>` guards
  `sockaddr_storage` with `#ifndef __MUSL__` while `<linux/socket.h>` defines it unconditionally,
  so the wrapper path is required to avoid a redefinition error.
- OHOS has no `install(1)`; `package()` copies the built products directly instead of relying on
  `make install DESTDIR=`.
- None of the nine tools supports `--version` (upstream returns `unrecognized option`); platform
  smoke checks use `-v` (rc=0, reports `4.4`).
- No source patches needed (0 patches).

## Versions
- 4.4 — built 2026-09-26 (OHOS/aarch64 native, path B: upstream has no tests; 118 checks on device
  = 67 supplementary unit + 45 consumer smoke (9 tools × 5) + 6 OHOS-specific; W3 passes and
  conan-verify G1–G4 pass. note: L2 smoke in conan-verify is SKIPPED, not passed — the nine tools
  reject `--version`/`--help`, so the version path is covered by test_package's `-v` checks instead;
  L4/L5 are likewise skipped when no cache path is present)
