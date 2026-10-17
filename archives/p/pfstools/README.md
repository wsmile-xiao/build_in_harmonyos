# pfstools

HDR image processing tools — a pipeline of command-line tools operating on the
PFS (Portable Floating-Set) format: converters (`pfsin*`/`pfsout*`), filters
(`pfscat`, `pfssize`, …), tone-mapping operators (`pfstmo_*`) and camera
calibration/alignment (`pfshdrcalibrate`, `pfsalign`).

## Homepage
https://pfstools.sourceforge.net/

## License
LGPL-2.1-or-later (see COPYING)

## Build System
CMake (top-level `cmake_minimum_required(VERSION 2.8.8)`)

## Dependencies
- **Core (`libpfs`): none** — plain C++ standard library.
- Optional (all disabled in this recipe, each with its own `-D WITH_*=OFF` switch):
  OpenEXR, ImageMagick, NetPBM, TIFF, Qt5, MATLAB, Octave, OpenGL/GLUT,
  FFTW, GSL, OpenCV, libexif; plus compiler-provided OpenMP.

## OHOS Adaptation
- Core build needs zero conan requirements: all optional dependencies are
  switched off via `WITH_*=OFF` cache variables (exact names in `2.2.0/conanfile.py`).
- `cmake_minimum_required(VERSION 2.8.8)` conflicts with CMake >= 4.0
  (compatibility with <3.5 removed, knowledge base E103 family);
  recipe pre-sets `CMAKE_POLICY_VERSION_MINIMUM=3.5` pending build verification.
- `BUILD_SHARED_LIBS=OFF` (R26) — static `libpfs.a`, no `/lib` pollution.
- Shell wrappers (`pfsin`, `pfsout`, `pfsindcraw`, camera scripts) are
  generated from `.in` templates by sed at configure time and installed to `bin/`.

## Versions
- 2.2.0 — recipe draft (non-build segment); source fetched and hashed, build pending.
