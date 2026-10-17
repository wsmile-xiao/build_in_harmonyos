# Flameshot

Flameshot is a powerful yet simple to use screenshot software with markup
tools, built as a Qt5 GUI application on OpenHarmony PC.

## Features

- Fullscreen, screen and region screenshot capture
- Annotation tools: arrows, markers, rectangles, circles, text, pixelate, etc.
- Pin captures on screen, save to file or clipboard
- Color picker and uploader (Imgur uploader disabled in this build)

## OpenHarmony adaptation

- Built with the Qt5 toolchain from the registry
  (`qt5-qtbase/5.15.2.2` + `qt5-qtsvg/5.15.2.1`); upstream 14.0.0 targets
  Qt6, so 14 portability patches bridge the Qt6→Qt5 API gaps.
- `qt5-qtbase` enters the dependency graph via a version override (upstream
  `qt5-qtsvg` pins 5.15.2, but Flameshot needs the DBus-enabled 5.15.2.2);
  the recipe therefore injects Qt include paths, Qt5 link libraries and
  `moc`/`rcc`/`uic` tool paths explicitly.
- Bundled `external/` dependencies (Qt-Color-Widgets, KDSingleApplication)
  are downloaded during `source()`; the build itself needs no network.
- Translation files (.qm) are not generated (no LinguistTools in the
  registry Qt5 build); UI is English.
- Strict OHOS execution contexts (CI worker sandbox, some shells) refuse
  to execute the produced GUI binary unless it is signed
  (`Operation not permitted`); `test_package` keeps the WARN fallback for
  sandboxed CI, and in non-sandbox contexts the binary is signed with
  `binary-sign-tool` (`selfSign`) and `flameshot --version` verified on-device.

## Dependencies

- `qt5-qtbase/5.15.2.2` (Qt5Core/Gui/Widgets/Network/DBus)
- `qt5-qtsvg/5.15.2.1` (Qt5::Svg)
- Bundled Qt-Color-Widgets and KDSingleApplication (fetched at source time)

## References

- Homepage: https://flameshot.org
- Source: https://github.com/flameshot-org/flameshot
- Version 14.0.0 (tag `v14.0.0`)
