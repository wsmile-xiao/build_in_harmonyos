# geocode-glib 3.26.4 notes

## Scope

GNOME geocoding helper library (Nominatim/OpenStreetMap backend).
Built in the **libsoup3 flavour** (`soup2=false` →
`libgeocode-glib-2.so`, pkg-config name `geocode-glib-2.0`) — the
exact dependency name libgweather 4.6.0's meson.build hard-requires
(`dependency('geocode-glib-2.0')`).

Dependency-first companion package (R36) for the libgweather 4.6.0
adaptation.

## Upstream

- Tag: 3.26.4 (gitlab.gnome.org/GNOME/geocode-glib)
- Tarball: https://download.gnome.org/sources/geocode-glib/3.26/geocode-glib-3.26.4.tar.xz
- SHA256: `2d9a6826d158470449a173871221596da0f83ebdcff98b90c7049089056a37aa`

## OHOS adaptations (libsoup 3.6.5-r1 recipe precedent)

- `soup2=false` → libsoup-3.0 flavour (geocode-glib-2.0).
- `enable-introspection=false` (g-ir-scanner cannot run against
  cross-built libs; gir is optional in upstream meson.build).
- `enable-gtk-doc=false`, `enable-installed-tests=false`.
- glib module .pc compat generation (gobject/gio/…): PkgConfigDeps
  only aggregates them into glib-2.0.pc, upstream meson.build asks
  for them individually.
- glib tool variables (glib_mkenums etc.) patched into glib-2.0.pc —
  gnome.mkenums needs them.
- SDK llvm bin prepended to PATH; ar pinned in the meson native file.
- `libgeocode-glib-2.so` re-signed with binary-sign-tool after
  install (OHOS loader requires a valid .codesign section).

## Upstream tests

- meson registers 3 tests: geo-uri (pure logic), geocode-glib API
  (mock Nominatim server via local JSON fixtures), mock-backend
  (GeocodeMockBackend object exercise). Cross-built binaries cannot
  run under `meson test` on the build host; the pure-logic surface
  (geo URI parsing, location construction, distance computation,
  name round-trip) is covered by the test_package consumer which runs
  on the OHOS host. The network-flavoured API/mock-backend tests
  need the Nominatim backend machinery — platform limitation reported
  as-is.

## Verification

- Local `conan create` (ohos-aarch64 profile) before PR; CI
  re-validates on a clean worker.
- Consumer test output: `ALL PASS` (version/coordinates/distance/
  geo-URI/name round-trips).
