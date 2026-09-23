# libkomparediff2

libkomparediff2 is the KDE library behind Kompare: it parses and models
unified/context/normal/RCS diff output and compares files programmatically
(`libkomparediff2.so`, SOVERSION 6, project/library version 6.0.0).

## OHOS adaptation

- Builds the official 26.04.0 release (CMake >= 3.16 + ECM, Qt6/KF6).
- Removes the only KF6KIO dependency (KIO is not published to ohpcd):
  `KIO::upUrl` in `src/kompareprocess.cpp` is reimplemented on plain QUrl,
  the save-path KIO stat/mkdir/file_copy jobs in `src/modellist.cpp` are
  replaced with QFile/QDir operations, and the
  `find_package(KF6 ... KIO)` / `KF6::KIOCore` link references are dropped
  (patches 0001-0005; same dependency-trimming approach as the kxmlgui
  `FORCE_DISABLE_KGLOBALACCEL=ON` precedent).
- `KF_IGNORE_PLATFORM_CHECK=TRUE` bypasses the KDE platform allowlist.
- `KF_SKIP_PO_PROCESSING=ON` skips translation-catalog generation
  (`ki18n_install(po)` honors it; kxmlgui 6.18.0 precedent).
- `ecm_generate_qdoc()` degrades gracefully: Qt6Tools/qdoc are not part of
  the ohpcd qtbase package, ECM 6.26 then only skips API-doc generation.
- Runs both upstream CTest entries headless (`QT_QPA_PLATFORM=offscreen`,
  `QTEST_GUILESS_MAIN`, embedded patch strings) inside conan create with
  BUILD_TESTING=ON.

## Dependencies

- `qtbase/6.11.1` supplies Qt6 Core/Widgets and Qt6Test (tests).
- `kcoreaddons/6.18.0`, `kconfig/6.18.0`, `ki18n/6.18.0`, `kxmlgui/6.18.0`
  supply the upstream `find_package(KF6 COMPONENTS CoreAddons Config XmlGui
  I18n)` components (KIO removed), aligned with the kxmlgui 6.18.0 graph.
- `ecm/6.26.0` supplies KDE cmake modules (no 6.18.0 ecm exists in the
  ohpcd baseline; kxmlgui 6.18.0 / kconfig 6.26.0 recipes use 6.26.0 too).

## References

- https://download.kde.org/stable/release-service/26.04.0/src/libkomparediff2-26.04.0.tar.xz
- https://invent.kde.org/libraries/libkomparediff2
