# kxl 1.2.4 OHOS adaptation notes

## Summary

- Package: `kxl/1.2.4` (Kacchan X Windows System Library, C library — not C++)
- Upstream: https://github.com/Quipyowert2/libKXL/releases/tag/v1.2.4
- Build: **CMake** (upstream autotools cannot bootstrap on the OHOS SDK
  worker — automake / libtoolize / aclocal are not installed; we ship a
  CMakeLists.txt in `patches/0006-cmake-build.patch`)
- Output: `libKXL.so` (canonical) AND `libKXL_static.a` (for the OHOS
  test_package smoke test, see "Tests" below), `KXL.h`, `kxl.pc`

## Dependencies (post-re-adaptation, R36 / R38)

| Dependency | Version | Role |
|------------|---------|------|
| libx11 | 6.4.0 | X11 client (upstream libX11 1.8.10; SONAME/cmd-pkgs id) |
| xorgproto | 2025.1 | transitive via libx11 |
| xtrans | 1.6.0 | transitive via libx11 |
| libxcb | 1.16 | transitive via libx11 |

The pulseaudio dependency from the previous adaptation (path A) has been
dropped — the OHOS audio framework is OHAudio, not PulseAudio, so we replace
`KXLsound.c` with a no-op stub in the conanfile build().

## Patches

| Patch | Purpose |
|-------|---------|
| `0003-stdint-fixed-width-types.patch` | LP64-safe `Sint32`/`Uint32` |
| `0004-display-name-snprintf.patch`  | Debian-derived overflow fix for `KXL_DisplayName` |
| `0006-cmake-build.patch`           | Add CMakeLists.txt (builds both `.so` + `.a`); overrides `CMAKE_RANLIB` for OHOS SDK's missing `llvm-ranlib` |
| `0007-kxl-pc-in.patch`             | Add `kxl.pc.in` template for downstream pkg-config consumers |

The previous 0001/0002/0005 patches were dropped along with the autotools
build path; they no longer apply.

## OHOS-specific build quirks

1. **OHOS toolchain find_package() masking**: The bundled
   `ohos.toolchain.cmake` sets `CMAKE_FIND_ROOT_PATH_MODE_PACKAGE=ONLY`,
   which prevents CMake from searching `CMAKE_PREFIX_PATH` (where conan's
   `CMakeDeps` writes the `<dep>-config.cmake` files). The recipe's
   `generate()` flips every `*_MODE_*` to `BOTH` for `os=OHOS` so the
   generators folder becomes searchable.

2. **Conan 2.x header propagation**: `cpp_info.requires` only mirrors link
   flags. To make `kxl::kxl` carry libx11's `INTERFACE_INCLUDE_DIRECTORIES`
   to consumers, we use `cpp_info.components["libkxl"].requires = [...]`
   and put the actual `libs = ["KXL"]` in the component.

3. **OHOS SDK's missing `llvm-ranlib`**: the bundled
   `ohos.toolchain.cmake` pins `CMAKE_RANLIB` to
   `${TOOLCHAIN_BIN_PATH}/llvm-ranlib`, but only `llvm-ar` ships in the
   SDK image. Static-link builds fail with `Error running link command:
   No such file or directory` without an override. The CMake patch
   detects this and runs `unset(CMAKE_RANLIB CACHE)` +
   `find_program(llvm-ranlib)`. Note: `set(CMAKE_RANLIB ... CACHE
   FILEPATH ...)` alone won't override an existing cache entry — the
   `unset` is mandatory.

4. **Audio backend stripped**: `KXLsound.c` (OSS/Pulse) is replaced by
   a no-op stub in `conanfile.build()` when `os=OHOS`, since `/dev/dsp`
   and `libpulse-simple` are unavailable. Apps that need audio
   integrate OHAudio directly; `KXL.h` keeps the audio API symbols
   for ABI compat.

## Tests

- **Layer 1 — upstream**: none. `KXL` ships no test suite, no `make
  check`, no CTest. Per `docs/TEST_QUALITY_SPEC.md` §3.3 we declare
  `upstream_tests: []` in `test_package/MANIFEST.yml`.
- **Layer 2 — test_package**: `test.c` is statically linked against
  `libKXL_static.a` and runs as `./test_kxl`. The static archive
  brings in the X.Org transport chain (`libx11` → `libxcb` → `libxau`
  → `libxdmcp`) at link time, so no `dlopen()` of `libKXL.so` is
  needed at runtime. This is the **only** way to get a runtime smoke
  test on OHOS: the loader's namespace ACL refuses to `dlopen()`
  shared libraries from `/storage/...` paths, and a `dlopen()`-based
  test crashed there.

   What `test.c` covers:
   - `Sint32` / `Uint32` are LP64-safe fixed-width integers
     (`_Static_assert`)
   - `KXL_Malloc(64)` returns non-NULL, the block is writable,
     `KXL_Free` doesn't crash
   - `KXL_DisplayName(":0")` doesn't crash on a synthetic display
     name (no X server required)
   - The X.Org transitive deps (`libx11` → `libxcb` → ...) are
     **link-resolvable** through `libKXL_static.a`, confirming the
     recipe's `requires=[...]` wiring works end-to-end

   What we **don't** cover (would need a live X server / display):
   - `KXL_CreateWindow`, `KXL_GetEvent`, `KXL_GetKeyboardState`
   - Pulse/OSS audio playback (already stubbed on OHOS)

## Local status

`conan create archives/k/kxl/1.2.4` succeeds on the HarmonyOS real device
with exit 0 and the binary outputs:

- `lib/libKXL.so.1.2.4`, `lib/libKXL.so.0`, `lib/libKXL.so`
- `lib/libKXL_static.a`
- `include/KXL.h`
- `lib/pkgconfig/kxl.pc`
- `licenses/COPYING`

The `test_package` consumer binary `test_kxl` statically linked against
`libKXL_static.a` + `libx11::libx11` runs `./test_kxl` from the
conanrun env and prints `kxl static-link api smoke ok`. Pass rate:
**100% (1/1 Layer 2 test, 5/5 assertions)**.