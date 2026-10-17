# SASM

Simple crossplatform IDE for NASM/MASM/GAS/FASM assembly development (Qt5 Widgets GUI).

## Homepage
https://github.com/Dman95/SASM

## License
GPL-3.0-or-later

## Build System
CMake — upstream ships a qmake project (`SASM.pro`); the recipe applies
`patches/0001-CMakeLists.txt.patch` (equivalent CMakeLists.txt with
AUTOMOC/AUTOUIC/AUTORCC) because the CI chain has no qmake consumer.

## Dependencies
- Qt 5.15.19 (Core / Gui / Widgets / Network) — QtSingleApplication sources are
  compiled in-tree, which is why Qt5Network is required

## OHOS Adaptation
- qmake → CMake rewrite: `patches/0001-CMakeLists.txt.patch` builds the same
  `sasm` executable target (no platform macros in the patch).
- `singleapplication` subtree: `qtlocalpeer.cpp` `#include`s
  `qtlockedfile.cpp` / `qtlockedfile_unix.cpp` inside namespace `QtLP_Private`,
  so the CMake source list must contain only `qtsingleapplication.cpp` and
  `qtlocalpeer.cpp` — listing the embedded `.cpp` files separately fails with
  `use of undeclared identifier 'QtLockedFile'` (knowledge draft E429).
- Source hash must be verified against the complete conan download (~22 MB):
  the GitHub release tarball is generated on the fly and truncated proxy bodies
  are common.

## Versions
- 3.15.0 — built 2026-10-01 (qt/5.15.19; test_package runs the IDE headless
  with `QT_QPA_PLATFORM=offscreen`, 3/3 assertions; upstream tests = 0)
