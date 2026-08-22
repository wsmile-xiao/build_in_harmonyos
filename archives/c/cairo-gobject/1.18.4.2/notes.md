# cairo-gobject 1.18.4 HarmonyOS PC adaptation notes

## Current Status

- Issue: #1860
- Upstream package: cairo 1.18.4
- Package target: cairo-gobject
- Source: cairo official release tarball
- Source URL: Launchpad mirror first, cairographics.org official release as fallback; both use SHA256 `445ed8208a6e4823de1226a74ca319d3600e83f6369f99b14265006599c32ccb`.
- Build system: Meson
- Current status: Conan recipe and test_package prepared; true-device `conan create` passed on 2026-08-05.

## W0 Dependency Check

- `cairo-gobject` is produced by the cairo source tree when Meson option `glib=enabled` is set.
- Existing `cairo/1.18.4` disables `glib`, so this package is prepared independently under `archives/c/cairo-gobject/1.18.4`.
- Selected dependencies:
  - `glib/2.84.0.1`
  - `pixman/0.46.4`
  - `libpng/1.6.58`
  - `freetype/2.14.3`
  - `fontconfig/2.18.1.1`
  - `zlib/1.3.1.1`

## Build Notes

- Meson options enable `glib`, `png`, `freetype`, `fontconfig`, and `zlib`.
- X11/Quartz/DWrite/LZO/libspectre/symbol lookup support is disabled to avoid extra platform dependencies.
- Upstream cairo tests are disabled in this recipe because they are large and require additional runtime assets; consumer behavior is covered by `test_package`.
- The recipe injects `llvm-ar` and `llvm-ranlib` into Meson's native file when the OHOS profile only provides `c`/`cpp` compiler paths.
- The recipe injects `pkg-config`/`pkgconf` into Meson's native file so Meson can resolve Conan-generated `.pc` dependencies on the device.
- On OHOS, the recipe sets a writable build-local `TMPDIR` before Meson configure so clang can create temporary files during compiler checks.
- The recipe patches cairo's top-level `meson.build` to run `version.py` through `python3`; direct script execution is blocked by the device filesystem policy.
- On OHOS, installed shared libraries are re-signed after Meson install.
- The recipe creates `libcairo-gobject.so.2`, `libcairo-gobject.so`, `libcairo.so.2`, and `libcairo.so` aliases when Meson cannot create shared-library symlinks.

## commands.json

- Not added. `cairo-gobject` installs libraries, headers, and pkg-config metadata; it does not install CLI tools.

## Local Verification

- Python AST recipe syntax check passed.
- `git diff --check` passed.
- Source metadata matches the existing `cairo/1.18.4` recipe.
- Local Conan validation was not run because Windows host has no `conan` command available.

## True-Device Verification

- Device: `currentUser@10.62.189.79:2222`
- Source cache: `/storage/Users/currentUser/Download/cairo-1.18.4.tar.xz`
- Source SHA256: `445ed8208a6e4823de1226a74ca319d3600e83f6369f99b14265006599c32ccb`
- Log: `/storage/Users/currentUser/codex-tests/cairo-gobject-1860/cairo-gobject-conan-create-1860-v6.log`
- Result: `conan create` passed; package build, OHOS signing, and `test_package` execution completed successfully.

## Re-run True-Device Command

```sh
export PATH=/data/service/hnp/cmake.org/cmake_4.1.2/bin:/data/service/hnp/ninja.org/ninja_1.13.1/bin:/storage/Users/currentUser/usr/local/bin:/data/service/hnp/bin:/bin:/system/bin
cd /storage/Users/currentUser/build_in_harmonyos
conan create archives/c/cairo-gobject/1.18.4 --profile:host=/storage/Users/currentUser/build_in_harmonyos/ci/conan/profiles/ohos-aarch64 --profile:build=/storage/Users/currentUser/build_in_harmonyos/ci/conan/profiles/ohos-aarch64 --build=missing
```
