# leela-zero 0.17

The upstream v0.17 archive contains empty Eigen and GoogleTest submodule
directories. The recipe downloads pinned Eigen 3.4.0 and GoogleTest 1.15.2
archives during `source()` so the build does not clone submodules.

OpenHarmony is built with `USE_CPU_ONLY=ON`. This keeps the upstream CPU
implementation and GoogleTest suite while avoiding a mandatory OpenCL runtime,
which is not a portable Conan dependency on OHOS.

The recipe overlays the small Boost.Format and Boost.Spirit header modules from
pinned Boost 1.90.0 module archives before Conan's Boost include directory.
This avoids rebuilding the large Boost CMake source package on OHOS workers
when the published binary lacks `boost/format.hpp`.

`build()` compiles the engine and executes the upstream `tests` binary.
