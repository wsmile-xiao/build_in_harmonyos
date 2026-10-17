# libapogee3 3.2+20221221183454 HarmonyOS PC adaptation notes

## Scope

- Upstream source: libapogee3 3.2+20221221183454 snapshot (the 2022-12-21
  18:34:54 Apogee Instruments driver source used by the Debian package).
- Formal package: shared `libapogee.so` plus the public headers under
  `include/libapogee/`.
- Declared Conan dependencies: `libusb/1.0.27` and `curl/8.15.0`.
- INDI is **not** a runtime dependency: the sources only include
  `indimacros.h` for two macros (`__BASE_FILE__`, `INDI_UNUSED`) and
  `target_link_libraries` lists only `${USB1_LIBRARIES}` and `${CURL}` — no
  INDI symbols are ever linked. A real INDI install would drag in Qt5/boost,
  so a stub header is generated at configure time instead.

## Upstream test status

The source tree ships no test suite: there is no `tests/` directory and
`CMakeLists.txt` declares no test target (verified against the Debian
orig.tar.gz). The library is a hardware camera driver whose functional tests
require a live USB/Ethernet Apogee camera, which CI cannot provide. The
package is whitelisted in `ci/config/no_official_test.txt`, so the L1
official-test check is skipped; the consumer test below still links and runs
the real installed library.

## Consumer test

`test_package/test_apogee.cpp` exercises the `CamModel` namespace — the part
of the library that is pure computation (no USB, network, or config-file
access): platform lookup by string and camera ID, firmware-revision
classification (Alta/Gen2 bounds), camera-ID masking, and the no-op firmware
revision. This end-to-end checks the installed headers and the shared
library's exported symbols (link + run), which is exactly what the OHOS
adaptation changes.

Result on HarmonyOS PC AArch64: **24 checks, 0 failures**
(`conan create` runs the test package automatically).

## OHOS adaptation points

1. **INDI stub header** — `generate()` writes `indimacros.h` next to the
   `INDI_INCLUDE_DIR` cache variable; the patched `CMakeLists.txt` feeds it to
   `include_directories()`.
2. **Missing include directory** — patch 0002 adds
   `include_directories(${USB1_INCLUDE_DIRS})`; the source includes
   `<libusb-1.0/libusb.h>`, which only resolves through the libusb package
   include root under cross-compilation.
3. **CMake 4.x minimum** — patch 0001 raises `cmake_minimum_required` to 3.15.
4. **Relocatable unversioned SONAME** — OHOS rules (same as the curl recipe)
   emit an unversioned, relocatable SONAME because HMDFS denies the SOVERSION
   symlink layout.

## Critical: install-time RPATH rewrite breaks the OHOS code signature

Symptom: `conan create` failed in the test package with
`Error loading libapogee.so (needed by test_apogee)`; `dlopen` reported
`Permission denied`.

Root cause (verified byte-by-byte on this device):

- lld writes a `.codesign` section (content-hash signature) into every shared
  object **at link time**, and the OHOS kernel enforces it on executable
  `mmap`.
- CMake embeds a build-tree RUNPATH pointing at the conan cache (the absolute
  libusb/curl lib dirs that `CMakeDeps` pins), so the linked `libapogee.so`
  contains a `DT_RUNPATH` of `/storage/.../libus.../p/lib:...` and its
  `.dynstr` holds that absolute path.
- `CMake(self).install()` then runs `file(RPATH_CHANGE OLD_RPATH "<absolute
  conan paths>" NEW_RPATH "")`, rewriting the file **after** the signature
  was written: 232 bytes change (the `.dynstr` path string + the
  `DT_RUNPATH` dynamic entry).
- The kernel's signature check then fails and refuses the executable mapping,
  which musl surfaces as the misleading `Permission denied` (it is an
  integrity failure, not a file-permission problem).

Why curl/libusb do not hit this: their build-tree RUNPATH is already the
relocatable `$ORIGIN/../lib:$ORIGIN` (set via `CMAKE_INSTALL_RPATH` at link
time), so install is a byte-identical no-op and the signature stays valid
(verified: build and package `libcurl.so` have identical sha256).

Fix in `conanfile.py` (`generate()`, OHOS + shared):

```cmake
CMAKE_SKIP_BUILD_RPATH = ON
CMAKE_SKIP_INSTALL_RPATH = ON
```

With both RPATHs skipped, the link step emits no RUNPATH and install has
nothing to rewrite, so the packaged file is byte-identical to the build-tree
file (verified: build and package `libapogee.so` sha256 are now equal) and
the `.codesign` section remains valid. Consumers resolve dependencies through
`LD_LIBRARY_PATH` (conanrunenv), which is how every other conan library on
OHOS is consumed anyway.

Verification of the fix:

- build-tree `libapogee.so` (pre-strip): dlopen OK;
- packaged `libapogee.so` before the fix: dlopen `Permission denied`;
- packaged `libapogee.so` after the fix: dlopen OK,
  `test_apogee` → `24 checks, 0 failures`.
