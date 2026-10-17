# gweather-locations

GNOME official world locations database, packaged as a data-only Conan
package: `Locations.bin` (GVariant normal-form database of world locations,
timezones, countries and METAR stations), `Locations.xml` + `locations.dtd`,
gettext translations, and a pkg-config file exposing the `locations_db` /
`locations_xml` / `locations_dtd` variables that libgweather 4.x consumes
through `dependency('gweather-locations')`.

## Versions

- 2026.2 - built (2026-10-02)

## Description

This package provides:
- `lib/gweather-locations/Locations.bin`: GVariant serialised database
  (magic `GWthDB01`; built host-endian, so os/arch stay in settings)
- `share/gweather-locations/Locations.xml` + `locations.dtd`: source data
- `share/locale/**/LC_MESSAGES/gweather-locations.mo`: translations
- `share/pkgconfig/gweather-locations.pc`: pkg-config variables for consumers

## OHOS Adaptation

- The build-time generator (`build-aux/gen_locations_variant.py`) needs
  python3 + PyGObject (`gi`). PyGObject is unavailable on the OHOS build
  host, so the recipe ships a pure-python `gi` shim implementing exactly the
  GLib.Variant serialisation subset the generator uses; PYTHONPATH injects
  it into both the meson python probe and the ninja-run generator.
- The shim must emit GVariant tuple framing offsets in reverse child order
  (matching GLib); a forward-order bug produces a Locations.bin that passes
  the magic check but crashes libgweather's parser. The shim in this recipe
  is the fixed version, byte-identical to a real GLib twin experiment.
- ninja is pinned by absolute path via NINJA (OHOS musl python subprocess
  cannot resolve bare-name hnp symlinks); the meson probe additionally gets
  LD_LIBRARY_PATH=/system/lib64.
- Upstream has no functional test suite; the only meson test entries are
  conditional lint tests (xmllint DTD validation of Locations.xml), which
  run for real when xmllint is on PATH. The test_package adds a pure-python
  GVariant deserializer that fully parses Locations.bin and validates
  structure and referential integrity as consumer evidence.

## Dependencies

- meson + ninja (build)
- python3 (build; generator, via the bundled `gi` shim)
- no C/C++ compile step, no conan package dependencies

## References

- https://gitlab.gnome.org/GNOME/gweather-locations
- https://download.gnome.org/sources/gweather-locations/
