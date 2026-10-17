# ksvg 6.26.0 Test Report

## Test Execution: ctest (integrated in conan create, BUILD_TESTING=ON)

### Result: PASS — 3/3 upstream tests + 1/1 consumer test

Upstream autotests are executed inside the Conan build via
`ctest --test-dir <build> --output-on-failure --no-tests=error`, headless
with `QT_QPA_PLATFORM=offscreen`. The KSvg rendering path used by the tests
is the QImage/QPainter software renderer (QSvgRenderer backend), so no X11/
Wayland session or GPU stack is required — this resolves the "runtime
dependency limitations" that blocked the previous (failed) attempt recorded
on main.

### Upstream CTest (N=3, measured with ctest -N):

| # | Test | Result | Time |
|---|------|--------|------|
| 1 | plasmasvg-framesvgtest | Passed | 0.16s |
| 2 | plasmasvg-imagesettest | Passed | 0.28s |
| 3 | plasmasvg-svgtest | Passed | 0.11s |

```
100% tests passed, 0 tests failed out of 3
Total Test time (real) = 0.55 sec
```

- plasmasvg-svgtest: Svg natural size/resize/element lookup (background.svgz
  + plasma theme fixtures)/stylesheet recoloring via KColorScheme.
- plasmasvg-framesvgtest: FrameSvg margins/contentsRect/imageSet/resizeMask/
  loadQrc assertions.
- plasmasvg-imagesettest: ImageSet theme selection/cache API assertions.

### Consumer test_package (N=1):

```
1/1 Test #1: test_ksvg ...... Passed 0.11 sec
ksvg/6.26.0 (test package): RUN: ./test_ksvg
PASS: KSvg Svg/FrameSvg API surface verified OK
```

test.cpp exercises the real API surface (R34): Svg validity, hasElement on
a rendered SVG, natural size/resize, image() (QImage software render),
elementRect, status/colorSet round-trips, color override round-trip, and
FrameSvg validity/resizeFrame/margins/marginSize/fixedMargins.

### Notes on the previous failed attempt (main residue)

The quality/test reports already on main describe tests failing due to
missing GUI runtime libraries (libKF6ConfigGui.so, libfontconfig, FreeType).
In this adaptation the runtime library resolution is handled by the recipe
(LD_LIBRARY_PATH from the conan graph + the ../../bin relative-NEEDED
compatibility links, kpackage 6.26.0 precedent), and the offscreen QPA
platform plugin from qtbase provides the headless QGuiApplication, so the
tests execute and pass on the OHOS PC device itself.
