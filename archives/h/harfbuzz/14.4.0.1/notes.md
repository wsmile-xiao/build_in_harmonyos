# HarfBuzz 14.4.0.1 adaptation notes (ICU component revision)

## Scope

`14.4.0.1` re-publishes the upstream **14.4.0** source with the Meson
`icu` option flipped to `enabled` (and `icu_builtin` left at its default
`false`), so the build emits a **standalone `libharfbuzz-icu.so`** plus
`harfbuzz-icu.pc` and installs `hb-icu.h`. Everything else inherits the
14.4.0 recipe (freetype=enabled, glib/gobject/cairo/zlib/graphite2=disabled,
subset/raster/vector/gpu + tests/utilities enabled).

## Why

WebKitGTK 2.48.1 requires `find_package(HarfBuzz 2.7.4 REQUIRED
COMPONENTS ICU)` in `Source/cmake/OptionsGTK.cmake`, and WebCore calls
`hb_icu_script_to_script()` (ComplexTextControllerHarfBuzz.cpp,
LocaleICU.cpp, ComplexTextControllerSkia.cpp). Every harfbuzz version
previously published to ohpcd (14.2.0 … 14.4.0) shipped `icu=disabled`
with no `libharfbuzz-icu`, so WebKitGTK's HarfBuzz configure check could
not pass. This revision adds exactly the missing ICU component.

## Dependency / build deltas vs 14.4.0

- `requirements()`: `+ self.requires("icu4c/78")`
  - icu4c/78 provides `lib/pkgconfig/icu-uc.pc` (Version 78.3), satisfying
    harfbuzz's `icu_min_version = '>= 49.0'`.
- `generate()`: after `PkgConfigDeps`, copy `icu4c.pc` → `icu-uc.pc` so the
  meson `dependency('icu-uc')` lookup resolves (same forwarding tectonic
  uses). PkgConfigDeps emits per-package `icu4c.pc`; the upstream meson file
  queries the canonical `icu-uc` module name.
- `project_options`: `"icu": "disabled"` → `"icu": "enabled"`.
- `package_info()`: new component `harfbuzz-icu`
  (`libs=["harfbuzz-icu"]`, `pkg_config_name="harfbuzz-icu"`,
  requires `harfbuzz` + `icu4c`) so consumers resolve
  `harfbuzz-icu.pc` / `HarfBuzz::ICU`.
- `test_package`: test.c now includes `<hb-icu.h>` and asserts
  `hb_icu_script_to_script(USCRIPT_LATIN) == HB_SCRIPT_LATIN`;
  CMakeLists links `harfbuzz::harfbuzz-icu` (assertion_count 9 → 10).

## Source

Same official upstream tarball as 14.4.0 (sha256 pinned in conandata.yml);
no source patches.
