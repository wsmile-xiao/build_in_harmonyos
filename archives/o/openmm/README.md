# openmm

OpenMM is a high-performance toolkit for molecular simulation. It can be used
either as a stand-alone application for running simulations, or as a library
for calling simulation routines directly from other code.

- Upstream: https://github.com/openmm/openmm
- License: LGPL-3.0-or-later

## OHOS adaptation

- CMake recipe (`8.1.2/conanfile.py`), CPU + Reference platforms and all
  CPU-able plugins (Amoeba, RPMD, Drude, CPU PME) are built for aarch64.
- GPU platforms (CUDA/OpenCL) disabled — no GPU SDK on OHOS PC.
- C/Fortran/Python wrappers disabled (not part of the C++ library deliverable).
- ELF `DT_SONAME` injected via `CMAKE_SHARED_LIBRARY_SONAME_C/CXX_FLAG`
  (native OHOS CMake has no Platform/HarmonyOS module defining the flag);
  plugins therefore record SONAME-based `DT_NEEDED` and load via `dlopen`.
- `OPENMM_PLUGIN_DIR` exported in runenv pointing at `lib/plugins`.
