# lcrq

LCRQ — C implementation of RFC6330 RaptorQ Forward Error Correction (FEC) codes for the Librecast project.

## Homepage
https://librecast.net/lcrq.html (upstream: https://git.sr.ht/~librecast/lcrq)

## License
GPL-2.0-or-later

## Build System
Autotools (configure + make)

## Dependencies
- None (pure C, libc only)

## OHOS Adaptation
- config.guess 2022-05-25 cannot recognize HarmonyOS (E007) — patched via `patch-autotools-ohos.pl`
- config.sub additionally required `linux-ohos*` in the kernel-os validation table (E007 patch script does not cover it)
- Upstream `src/Makefile.in` is hand-written, in-source only (no VPATH) — conan recipe uses `basic_layout(self, build_folder=".")`
- Upstream tarball contains dangling symlinks `test/all/*.test` (resolved at build time) — incompatible with shutil.copytree on HMDFS
- Shared library only (`all: $(SOFILE)`); no static build target upstream

## Versions
- 0.3.1 — built 2026-09-19 (upstream `make test` 19 run / 18 OK / 0 FAIL / 1 SKIP; test_package encode/decode roundtrip OK)
