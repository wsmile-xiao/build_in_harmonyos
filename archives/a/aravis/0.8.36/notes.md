# aravis 0.8.36 adaptation notes

## 2026-07-18

- Claimed for the points contest in issue #1234:
  https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/issues/1234
- Source and Homebrew formula checked:
  - https://github.com/AravisProject/aravis/releases/download/0.8.36/aravis-0.8.36.tar.xz
  - https://raw.githubusercontent.com/Homebrew/homebrew-core/HEAD/Formula/a/aravis.rb
- Local W0 preflight command attempted:
  `bash ci/scripts/preflight_check.sh aravis/0.8.36`
- Current workstation is Windows without a working WSL/OHOS shell, so the
  preflight script did not run. Full dependency publication checks and
  `conan create` must be rerun in OpenDesk/OHOS.

## Dependency decisions

- Required for the first default core-library package: `glib`, `libxml2`, and
  `zlib`.
- `glib/2.84.0`, `libxml2/2.15.3`, and `zlib/1.3.1.1` have consumable Conan
  packages in the OHOS precheck environment.
- `libusb/1.0.27` has historical metadata/patches/notes in this checkout, but
  no consumable Conan recipe/package was found in the OHOS precheck remote, so
  USB3 Vision support is disabled in the first default package and left as a
  follow-up after libusb publication.
- `gtk+/3.24.38` has metadata in this checkout, but the viewer is disabled
  for the first pass to keep validation focused on the core camera library.
- `gstreamer/1.28.3` has local metadata but no CI input recipe in this
  checkout, so the GStreamer plugin is disabled for the first pass.
- The existing libusb notes also document SELinux/device-I/O limitations on
  OpenHarmony application domains, so USB hardware validation needs a separate
  privileged-device follow-up even after libusb is published.

## Upstream tests

With `tests=true` and introspection disabled, `tests/meson.build` defines
seven C tests:

- evaluator
- buffer
- misc
- dom
- genicam
- fake
- fakegv

Additional examples are built but not registered as Meson tests.
