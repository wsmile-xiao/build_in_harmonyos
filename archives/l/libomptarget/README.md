# libomptarget

libomptarget is the OpenMP offloading **target runtime library** from the LLVM
`openmp` project (`openmp/libomptarget`). It provides the host-side offloading
runtime (`libomptarget.so`) and target plugins used by clang-generated OpenMP
`target` regions:

- `libomptarget.so` — target-agnostic offloading runtime (device image loading,
  plugin management, `__tgt_*` API consumed by clang).
- `libomptarget.rtl.aarch64.so` — aarch64 generic-ELF64 NextGen plugin
  (dlopened-libffi mode, no system libffi required).
- `libomp.so.5` — host OpenMP runtime, bundled as the `omp` link dependency of
  libomptarget (SONAME `libomp.so.5`).

## OHOS adaptation

Version **18.1.8** is adapted for **HarmonyOS PC (aarch64)** as a standalone
CMake build (`OPENMP_STANDALONE_BUILD=ON`, `OPENMP_ENABLE_LIBOMPTARGET=ON`).

- **LLVM dependency** — `find_package(LLVM REQUIRED)` needs an LLVM package.
  `llvm/18.1.8` is **not** published in the ohpcd artifact repository, while
  `llvm/20.1.0` is. The libomptarget 18.1.8 sources were **verified** to
  compile and link against the LLVM 20.1.0 headers/libs (one JIT.cpp API
  adaptation needed, see patch 0005). The recipe therefore
  `requires("llvm/20.1.0")`.
- **Platform recognition** — CMake has no built-in `Platform/HarmonyOS`
  module; `Platform/HarmonyOS.cmake` (`include(Platform/Linux)`) is injected
  into `CMAKE_MODULE_PATH` so the "HarmonyOS" system is recognised and
  `CMAKE_SHARED_LIBRARY_SONAME_*_FLAG` is set (otherwise `libomptarget.so`
  would carry a build-tree-relative `DT_NEEDED`).
- **SONAME policy** — built shared libraries keep upstream-style SONAMEs:
  `libomptarget.so.20.1`, `libomptarget.rtl.aarch64.so.20.1`, `libomp.so.5`.
  The `.20.1` suffix on libomptarget mirrors the LLVM-versioned SONAME scheme
  used when libomptarget is built in-tree with LLVM (expected behaviour, it is
  not the upstream libomptarget own ABI version).
- **Plugins** — only the aarch64 generic-ELF64 plugin is built (host CPU
  offload); CUDA/AMDGPU plugins require the corresponding hardware/drivers and
  are skipped. `LIBOMPTARGET_BUILD_DEVICERTL_BCLIB=FALSE` disables DeviceRTL,
  which needs clang `-fopenmp-targets` GPU bitcode generation unavailable on a
  GPU-less host.
- **pthread_cancel** — HarmonyOS lacks POSIX thread cancellation (like
  Android); `KMP_CANCEL_THREADS` is undefined for `__OHOS__` (knowledge E081).

## Dependencies

- `llvm/20.1.0` — LLVMConfig.cmake + libLLVM.so.20.1 + headers (published).

## References

- https://github.com/llvm/llvm-project/tree/llvmorg-18.1.8/openmp/libomptarget
- https://openmp.llvm.org
- https://releases.llvm.org/18.1.8/docs/OpenMPSupport.html
