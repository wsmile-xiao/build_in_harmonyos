# libdbi

libdbi is a database-independent abstraction layer for C applications. This
archive adapts upstream 0.9.0 for OpenHarmony aarch64. The `r5` suffix is the
competition task revision and does not change the upstream API version.

## Package contents

- Shared `libdbi` core library
- Public `dbi/dbi.h`, `dbi/dbi-dev.h` and `dbi/dbd.h` headers
- `dbi.pc` pkg-config metadata
- LGPL-2.1-or-later license text

Database drivers are distributed separately by upstream and are not bundled.

## OpenHarmony adaptation

- Recognize `aarch64-unknown-linux-ohos` for native and cross builds.
- Avoid configure-time temporary-directory permissions incompatible with HMDFS.
- Disable documentation and optional libltdl integration.
- Use the system dynamic-loader API and package only the core library.

## Validation

- Official source SHA256: verified.
- Upstream `make check`: executed by the recipe; no runnable tests are declared.
- Consumer API test: 29/29 assertions passed, including initialization with no drivers.
- OpenHarmony API 20 target: AArch64 library and consumer compiled and linked.
- Target library: ELF64 AArch64, SONAME `libdbi.so.1`, only `libc.so` required.
- HarmonyOS PC runtime: not claimed because no device was borrowed.

The competition pipeline remains the final target-runtime verification.

## References

- Homepage: https://libdbi.sourceforge.net/
- Source: https://sourceforge.net/projects/libdbi/
- License: LGPL-2.1-or-later
