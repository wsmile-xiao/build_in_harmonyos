# Quality Report — ksvg 6.26.0

**Verdict**: PASS

## G1 Binary Integrity: PASS
- libKF6Svg.so.6.26.0 (SONAME libKF6Svg.so.6, injected via CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG)
- org.kde.ksvg QML plugin (libcorebindingsplugin.so → lib/qml/org/kde/ksvg)
- Headers: KSvg/Svg, KSvg/FrameSvg, KSvg/ImageSet (+ ksvg_version.h, ksvg_export.h)
- 0 errors, 0 warnings

## G2 Functional: PASS
- Upstream CTest 3/3 (plasmasvg-svgtest/framesvgtest/imagesettest, offscreen QImage software rendering)
- test_package 14 assertions all pass (Svg/FrameSvg API surface incl. image() render)
- 0 errors, 0 warnings

## G3 Portability: PASS
- KF_IGNORE_PLATFORM_CHECK + full OHOS profile build
- No hardcoded /lib, /usr paths in outputs; relocatable layout (lib/, lib/qml/)
- 0 errors, 0 warnings

## G4 Archive: PASS
- manifest.yaml complete (build_system: cmake, sha256, deps, patches)
- conanfile.py + conandata.yml + test_package/ complete (CI inputs)
- Patches: 3 (0001-lower-kf-dep-version, 0002-ohos-framecontrast-backport, 0003-ohos-qml-kirigami-6.18-compat)
- notes.md, reports/ (test-report, quality-report, w3-local-ci) present
- 0 errors, 0 warnings
