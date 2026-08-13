# sane-backends 1.2.1 adaptation notes

## Scope

This initial OpenHarmony build targets the portable SANE core, shared backend library, and command-line frontends. It intentionally disables Linux service integration and optional hardware-specific integrations until they can be validated independently.

## W0 dependency gate

Published recipes verified before source work:

- libusb/1.0.27
- libjpeg/10
- libpng/1.6.58
- libtiff/4.7.2
- curl/8.15.0
- libxml2/2.15.3

## Expected OpenHarmony configuration

- Disable Avahi, systemd, V4L, SNMP, Poppler, and gphoto2.
- Build the portable test and Genesys backends; hardware transport validation remains deferred until a supported scanner is available on OpenHarmony.
- Compile every upstream `make check` test target: five SANEI tests, the Genesys unit suite, and `sane-desc` for all 14 upstream output modes.
- Execute those 20 upstream checks only on a deployed OpenHarmony runtime because the cross-build worker cannot load target dynamic dependencies.
- Validate the packaged test backend by initializing SANE, enumerating a device, opening it, closing it, and shutting down.

## OpenHarmony build-system exception

The official 1.2.1 release asset is an Autotools source archive without generated build files. The recipe regenerates `configure` and `Makefile.in` from source files, then applies a narrow OpenHarmony HMDFS compatibility adjustment to generated `configure`: Autoconf cannot create `subs1.awk` or `_stdint.h` in its `conf*` temporary subdirectory on this filesystem. The adjustment keeps these temporary files in the build root and preserves that root during cleanup. This is the approved R6 exception for this recipe; no generated source artifact is committed.

The upstream `make check` binaries are cross-compiled for OHOS and require Conan dynamic dependencies deployed on a target runtime. They are built but not executed during the host cross build. The substantive Conan consumer test calls `sane_init`, `sane_get_devices`, `sane_open`, `sane_close`, `sane_strstatus`, and `sane_exit` when the deployed target sets `SANE_RUN_TARGET_TESTS=1`.
---

**编译结束**: 2026-08-08 17:01
**最终状态**: built
