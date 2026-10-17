# atk 2.38.0.1 HarmonyOS PC adaptation notes

## Current Status

- Issue: #1857
- Package version: 2.38.0.1
- Upstream package: ATK 2.38.0
- Source: GNOME official tarball
- Build system: Meson
- Local status: Conan recipe and test_package prepared; true-device `conan create` passed.

## W0 Dependency Check

- Required upstream dependencies:
  - `glib-2.0 >= 2.38.0`
  - `gobject-2.0 >= 2.38.0`
- Selected Conan dependency:
  - `glib/2.84.0.1`
- `glib/2.84.0.1` already provides component pkg-config names for `glib-2.0` and `gobject-2.0`, plus GLib build tools such as `glib-mkenums` and `glib-genmarshal` in `bin/`.

## Build Notes

- Meson options:
  - `-Ddefault_library=shared`
  - `-Dwrap_mode=nodownload`
  - `-Dintrospection=false`
  - `-Ddocs=false`
- Introspection is disabled to avoid running `g-ir-scanner` and loading Python extension modules during the package build.
- The recipe prepends dependency `bin/` directories to `PATH` so Meson can find GLib code-generation tools.
- The generated `glib-2.0.pc` / `gobject-2.0.pc` files are augmented with GLib code-generation tool variables required by Meson's GNOME module.
- GLib Python tool scripts are invoked through generated Python wrappers because `/usr/bin/env` is not executable on the tested OHOS device.
- On OHOS, the recipe links against the `libintl.so` shipped by the selected GLib package to resolve `g_libintl_*` symbols expanded from GLib i18n headers.
- The recipe creates `libatk-1.0.so.0` and `libatk-1.0.so` aliases when Meson cannot create shared-library symlinks on OHOS.
- `TMPDIR`, `TMP`, and `TEMP` are redirected to a build-local writable directory.
- Installed OHOS ELF shared libraries are re-signed after `meson install`.

## Patch Notes

- `0001-treat-harmonyos-as-linux-for-linker-flags.patch` extends the upstream Linux linker flag check to `harmonyos` because Meson reports the OHOS host system as `harmonyos`.
- The previous historical `intl-wrapper` source patch is not reused. Instead, the recipe links the GLib package's `libintl.so`, which exports the required `g_libintl_*` symbols, keeping the upstream ATK source patch surface smaller.

## Upstream Tests

- Upstream Meson defines 5 tests:
  - `testdocument`
  - `testrole`
  - `testrelation`
  - `teststateset`
  - `testvalue`
- The recipe keeps these tests built by upstream Meson and runs `meson.test()` when the host binary can run.
- The supplied `test_package` compiles and runs a C consumer that includes `<atk/atk.h>`, checks `atk_get_major_version()/atk_get_minor_version()`, and resolves core GTypes.

## commands.json

- Not added. ATK installs a library, headers, and pkg-config metadata; it does not install CLI tools.

## Local Verification

- Source SHA256 verified:
  - `ac4de2a4ef4bd5665052952fe169657e65e895c5057dffb3c2a810f6191a0c36`
- Patch applies to the extracted 2.38.0 source with `git apply --check`.
- Python recipe syntax check passed.
- `git diff --check` passed.
- Local Conan validation was not run because Windows host has no `conan` command available.

## True-Device Verification

- Device: `currentUser@10.62.189.79:2222`
- Command log: `/storage/Users/currentUser/codex-tests/atk-1857/atk-conan-create-1857-v9.log`
- Result: `conan create` passed.
- Package created: `atk/2.38.0.1#ae879ba863f19506f7adc5118d246271:68e44dcc4e462f75c52f2f88149f4056bad74a52#3b7e0d01d97a9f9425f9e02a9d7a267e`
- Upstream Meson tests: 5/5 passed.
  - `testdocument`
  - `testrole`
  - `testrelation`
  - `teststateset`
  - `testvalue`
- `test_package`: CMake consumer built and `./test_atk` ran successfully.

## Reproduce True-Device Command

```sh
export PATH=/data/service/hnp/cmake.org/cmake_4.1.2/bin:/data/service/hnp/ninja.org/ninja_1.13.1/bin:/storage/Users/currentUser/usr/local/bin:/data/service/hnp/bin:/bin:/system/bin
conan create archives/a/atk/2.38.0.1 --profile:host=/storage/Users/currentUser/build_in_harmonyos/ci/conan/profiles/ohos-aarch64 --profile:build=/storage/Users/currentUser/build_in_harmonyos/ci/conan/profiles/ohos-aarch64 --build=missing
```
