# Geogram

Geogram is a BSD-3-Clause C++ library of geometric algorithms and mesh data
structures from INRIA.

- Upstream: https://github.com/BrunoLevy/geogram
- Release: 1.10.1
- Build system: CMake
- Package form: `geogram` shared or static library

This adaptation disables the graphics viewer, TBB, and legacy numerical
plugins so the library-only package remains self-contained. The upstream
release asset includes its vendored third-party sources; no Conan dependency
is required.

