# SOPT

Sparse optimisation C++17 library with Eigen and TIFF image support.
Dependencies: Eigen 3.4.0, libtiff 4.7.2; build tests use Catch2 3.8.1.
Use Conan CMakeDeps, `find_package(sopt CONFIG REQUIRED)`, and link `sopt::sopt`.

This recipe builds the single-process CPU configuration. MPI, OpenMP and ONNX are disabled.
v5.0.1 contains the upstream version constant 5.0.0; it is preserved.
Local verification uses OHOS7 Beta AArch64 QEMU with OHOS6 package metadata.
See `5.0.1/reports/test-report.md` for tested scope; formal OHOS6 and remote CI remain unverified.
