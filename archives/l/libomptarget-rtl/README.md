# libomptarget-rtl

libomptarget-rtl is the **RTL plugin library** of the LLVM OpenMP offloading
runtime, from the LLVM `openmp` project (`openmp/libomptarget/plugins-nextgen`).
It contains the target plugins (`libomptarget.rtl.*.so`) that the offloading
runtime (`libomptarget.so`) dlopens at runtime to drive a specific target.

This package mirrors the Alpine `libomptarget-rtl` packaging: it ships the RTL
plugin libraries only (not the `libomptarget.so` main runtime, not `libomp.so`,
not the OpenMP API headers — those belong to their own packages).

- `libomptarget.rtl.aarch64.so` — aarch64 generic-ELF64 NextGen plugin
  (dlopened-libffi mode, no system libffi required).

## OHOS adaptation

Version **18.1.8** is adapted for **HarmonyOS PC (aarch64)** as a standalone
CMake build (`OPENMP_STANDALONE_BUILD=ON`, `OPENMP_ENABLE_LIBOMPTARGET=ON`).

- **LLVM dependency** — the RTL plugin links `libLLVM.so.20.1` (NEEDED).
  `llvm/18.1.8` is **not** published in the ohpcd artifact repository, while
  `llvm/20.1.0` is. The libomptarget 18.1.8 sources were **verified** to
  compile and link against the LLVM 20.1.0 headers/libs (one JIT.cpp API
  adaptation needed, see patch 0005). The recipe therefore
  `requires("llvm/20.1.0")`.
- **Platform recognition** — CMake has no built-in `Platform/HarmonyOS`
  module; `Platform/HarmonyOS.cmake` (`include(Platform/Linux)`) is injected
  into the generators dir so the "HarmonyOS" system is recognised and
  `CMAKE_SHARED_LIBRARY_SONAME_*_FLAG` is set (otherwise the plugin would
  carry a build-tree-relative `DT_NEEDED`).
- **No LTO** — the libomptarget CMakeLists enables `LIBOMPTARGET_USE_LTO`
  (appends `-flto` after `CMAKE_CXX_FLAGS`); LTO-built shared libraries are
  rejected by the HarmonyOS musl loader. The recipe forces
  `LIBOMPTARGET_USE_LTO=FALSE` + `-fno-lto` so the plugin is plain machine
  code.
- **No system libffi** — `CMAKE_DISABLE_FIND_PACKAGE_FFI=TRUE` forces the
  self-contained "dlopened libffi" plugin mode (a system libffi on the build
  host would otherwise switch the plugin into link-against-libffi mode and
  break on the `ffi/ffi.h` include layout).
- **Plugins** — only the aarch64 generic-ELF64 plugin is built (host CPU
  offload); CUDA/AMDGPU plugins require the corresponding hardware/drivers and
  are skipped. `LIBOMPTARGET_BUILD_DEVICERTL_BCLIB=FALSE` disables DeviceRTL.
- **pthread_cancel** — HarmonyOS lacks POSIX thread cancellation (like
  Android); `KMP_CANCEL_THREADS` is undefined via the
  `LIBOMP_HAVE_PTHREAD_CANCEL` capability macro (knowledge E081).
- **Runtime dlopen limitation** — the plugin links libLLVM's `LLVM_20.1`
  versioned symbols; HarmonyOS musl `dlopen()` returns EACCES for ELF with
  `.gnu.version_r` (same known limitation as the libomptarget main library).
  The test_package verifies install+link of the plugin and skips runtime with
  that reason documented.

## Dependencies

- `llvm/20.1.0` — LLVMConfig.cmake + libLLVM.so.20.1 + headers (published).

## References

- https://github.com/llvm/llvm-project/tree/llvmorg-18.1.8/openmp/libomptarget
- https://openmp.llvm.org
- https://releases.llvm.org/18.1.8/docs/OpenMPSupport.html
