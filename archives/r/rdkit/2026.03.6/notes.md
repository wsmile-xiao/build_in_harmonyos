# RDKit 2026.03.6 — Adaptation Notes

## Build System
CMake (minimum 3.18)

## Dependencies
- boost/1.91.0.1 (serialization, regex, iostreams, system, filesystem, thread)
- eigen/3.4.1 (3D descriptors)
- freetype/2.14.3 (molecular drawing)
- libpng/1.6.58.1 (image output)
- zlib/1.3.1.1 (compression)

## CMake Options
- CMAKE_SYSTEM_NAME=Linux (E092: CMake doesn't recognize HarmonyOS)
- RDK_BUILD_PYTHON_WRAPPERS=OFF (no Python on OHOS CI)
- RDK_BUILD_CPP_TESTS=OFF (disable C++ test suite)
- RDK_BUILD_INCHI_SUPPORT=OFF (there is an optional download)
- RDK_BUILD_AVALON_SUPPORT=OFF (optional, not needed)
- RDK_INSTALL_INTREE=OFF (install to prefix layout)
- RDK_INSTALL_STATIC_LIBS=ON (30+ static libraries)

## Key Adaptations
This is a cross-compile build for OHOS PC (aarch64). The compiler is clang 15 with libc++. System name is set to Linux as a workaround for CMake's platform detection.

RDKit produces many libraries (RDGeneral, GraphMol, SmilesParse, etc.). The conan recipe auto-collects all installed libraries. Headers are installed to include/rdkit/.

## Source
Tag: Release_2026_03_6 (github.com/rdkit/rdkit)
URL: https://github.com/rdkit/rdkit/archive/refs/tags/Release_2026_03_6.tar.gz
