# xmppc 0.1.0 HarmonyOS adaptation notes

## Package

- Upstream: https://codeberg.org/Anoxinon_e.V./xmppc, release 0.1.0
- Product: XMPP command-line client (`xmppc`), not a linkable library
- Target: HarmonyOS PC, AArch64 (`os=OHOS`, `arch=armv8`)
- Build system: GNU Autotools
- License: GPL-3.0-or-later

## Build

The official Codeberg archive endpoint timed out in this environment. `conandata.yml` therefore uses the xmppc 0.1.0 original source archive from Ubuntu's official archive and verifies its measured SHA-256 (`c43e17445eccd18c3d87660b84e6b10e3613670e5e09fee2830726f026596be2`). The upstream project remains [Anoxinon e.V.'s Codeberg repository](https://codeberg.org/Anoxinon_e.V./xmppc). The release tree has `configure.ac` but no generated `configure`, so the recipe runs `autoreconf --install --force` with published Automake and Libtool build tools.

For native OHOS/armv8 profiles, Autoconf receives `--build=aarch64-unknown-linux-gnu` and `--host=aarch64-unknown-linux-ohos`. The distinct triplets prevent configure from trying to execute SDK-built feature probes. GLib and libstrophe are discovered through pkg-config. The recipe uses `glib/2.88.0.1`, which satisfies the upstream `glib-2.0 >= 2.40` check and shares the zlib revision selected by `libstrophe/0.14.0`. It uses the published C-only `gpgme/1.24.0` package because xmppc does not need GPGME's optional Qt bindings. The recipe supplies include and library paths for GPGME, libassuan, and libgpg-error because upstream probes them with `AC_CHECK_LIB` but does not import Conan's paths, while the OpenPGP source is always compiled.

HarmonyOS dependency packages include relocated static libtool `.la` metadata with `libdir=//lib`. To avoid those stale references, the OHOS build links the application directly with the configured compiler. Other dependencies remain dynamically linked and Conan's run environment supplies their library paths to consumers.

The upstream PGP helper used GNU-only `strndupa`, which HarmonyOS Clang does not declare. The portability patch replaces it with a length-checked allocation and bounded `memcpy`; malformed short input and allocation failure return `NULL`.

The `conan-pr-check` worker exposed an HMDFS permission issue while `config.status` created `./confXXXXXX/subs1.awk`. Autoconf generates that step with `umask 077`; on HarmonyOS setgid directories, the resulting temporary directory can lack the group permissions HMDFS uses for access checks. For OHOS builds, the recipe changes the generated `configure` script to use `umask 022` before it emits and runs `config.status`. This is a generated-build-script workaround and does not modify upstream source files.

The package installs the `xmppc` executable, upstream documentation and manual page, and the license under `licenses/`.

## Tests

Upstream test inventory (R51): there is no upstream `tests/` directory, `Makefile.am` defines neither `TESTS` nor a `check` target, and there are no CTest or pytest registrations. There are zero upstream tests to run; `make check` is unavailable for this release.

The Conan consumer test executes the packaged `xmppc --help` and checks its exit status, usage banner, and help option text. The OHOS/armv8 test also asserts AArch64 target settings and runs on the supplied HarmonyOS 6.0 device. W3 ran one Conan consumer test on the device; it passed (1/1).

## Verification record

Verification on 2026-10-01: the local W3 pipeline passed on the device with Conan 2.29.1 and profile `ohos-aarch64`; L0, L1, and L5 passed, including `conan create` and the consumer runtime test. The HarmonyOS-specific `xmppc --help` test passed. W3's standalone L2 smoke emitted a non-blocking warning: without Conan's run environment, the loader cannot find `libgpgme.so.11`, `libstrophe.so.0`, `libexpat.so`, `libassuan.so.9`, and `libgpg-error.so.0`. The formal consumer test uses `VirtualRunEnv` and passed. L4 also warned because its text scan matches the upstream `strcpy` line removed by the portability patch; the patched implementation uses `memcpy` and checks the allocation result.

The PR worker failure at `config.status` was traced to its HMDFS temporary-directory permissions. On 2026-10-02, the updated recipe completed `conan create` on the HarmonyOS 6.0 AArch64 device, including the HarmonyOS-specific CLI consumer test (1/1). The direct SSH test used `/system/bin/sh` because the HNP Bash cannot resolve its working directory when launched outside the worker service; the PR worker's HNP Bash CI rerun remains the final check for that environment.
