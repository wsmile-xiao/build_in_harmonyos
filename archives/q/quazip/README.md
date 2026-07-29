# QuaZip

QuaZip is a Qt/C++ wrapper over minizip for ZIP archive access.

## OpenHarmony adaptation

- Uses Conan-provided Qt 5 and zlib dependencies.
- Maps the Qt Conan dependency to the upstream Qt5 CMake package name.
- Runs the upstream qztest suite and a packaged ZIP round-trip consumer test.
