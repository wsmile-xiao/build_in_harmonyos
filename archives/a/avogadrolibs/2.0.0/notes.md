# avogadrolibs 2.0.0 adaptation notes

The recipe intentionally targets the reusable headless C++ libraries. Qt 6,
OpenGL, Python bindings, libarchive, libmsym, spglib, JKQTPlotter, HDF5, and
MMTF are optional upstream features and are disabled for the initial OHOS
candidate. Core, Calc, IO, and QuantumIO remain enabled.

The official tag `2.0.0` resolves to upstream commit
`d41dbf36dd92fcf275f25bb5f3ad4063a838ed3a`. The Conan payload uses the stable
official GitHub tag archive and its controlled-download SHA256.

The recipe owns an OHOS CMake toolchain: it selects the installed `OHOS`
platform, the SDK sysroot, `aarch64-unknown-linux-ohos`, SDK clang/clang++,
and `llvm-ar`/`llvm-ranlib`. CMakeDeps is admitted as a rooted target package
location and `Eigen3_DIR` is set to that generator directory, while programs
remain host-resolved (`PROGRAM=NEVER`) and libraries/includes/packages remain
target-rooted.

`testing=True` is an opt-in diagnostic configuration and formally uses the
repository's OHOS `gtest/1.17.0` through `test_requires`. It is not enabled by
the default headless package because avogadrolibs 2.0.0 unconditionally asks
for Qt6 Core, Widgets, Network, and Concurrent in its test CMakeLists even
when `USE_QT=OFF`. The diagnostic therefore records a configure boundary at
missing OHOS Qt6, not a test pass.

Upstream exposes a CTest entrypoint when configured with `ENABLE_TESTING=ON`.
This headless Conan recipe deliberately configures `ENABLE_TESTING=OFF`, so
upstream CTest is **NOT_RUN** and must not be reported as PASS. Static source
inspection found 18 `add_test()` call sites, but that source count is not an executed-test total. Authoritative CI instead builds, links, and runs the
Conan `test_package` consumer.

Upstream CTest remains **NOT_RUN**: configure cannot complete past the
unconditional Qt6 closure. Alternative validation is the real OHOS
configure/compile/link probe, explicit-profile Eigen/GTest discovery, and the
authoritative Conan consumer checks. Residual risk is uncompiled Qt-coupled
upstream test logic and absent OHOS Qt6 packages.
