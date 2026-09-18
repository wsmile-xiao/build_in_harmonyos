# OpenMM 8.1.2 — OHOS Adaptation Notes

## Software Overview

OpenMM is a high-performance toolkit for molecular simulation. It provides:
- A C++ library for molecular dynamics simulation
- Multiple compute platforms: Reference (portable), CPU (optimized), CUDA, OpenCL
- Plugins: Amoeba, RPMD, Drude, CPU PME
- C and Fortran API wrappers (generated from C++ API)
- Python wrappers (requires Swig)

## Build System

- **Build system**: CMake (minimum 3.17)
- **C++ standard**: C++11
- **Source**: https://github.com/openmm/openmm/archive/refs/tags/8.1.2.tar.gz

## Dependencies

- **No external Conan requires** — all internal libraries are bundled:
  - jama, quern, lepton, sfmt, lbfgs, hilbert, csha1, pocketfft, vkfft, irrxml, asmjit
- **No tool_requires** — wrappers are disabled; CMake's
  `find_package(PythonInterp)` is optional (called without REQUIRED) and
  under CMake 4.x the removed module just degrades to a harmless fallback
- **System libraries**: pthreads, dl, rt (auto-linked by CMake on Linux/OHOS)

## OHOS Adaptation Decisions

### GPU Platforms Disabled (Platform Limitation)
- `OPENMM_BUILD_CUDA_LIB=OFF` — no CUDA toolkit on OHOS PC
- `OPENMM_BUILD_OPENCL_LIB=OFF` — no OpenCL on OHOS PC
- (OpenMM 8.1.2 has no HIP platform — that option does not exist in this release)
- These are auto-detected by CMake (find_package QUIET), so they would be disabled anyway
- Explicitly setting OFF avoids unnecessary find_package calls

### CPU Platform Kept
- `OPENMM_BUILD_CPU_LIB=ON` — optimized CPU platform for aarch64
- Uses asmjit for JIT expression compilation (built-in library)
- ARM64 architecture detected by TargetArch module: `add_definitions(-D__ARM64__=1)`

### All Plugins Kept
- Amoeba, RPMD, Drude, CPU PME — all built as shared libraries
- These provide additional force field and simulation capabilities

### C and Fortran Wrappers Disabled
- `OPENMM_BUILD_C_AND_FORTRAN_WRAPPERS=OFF`
- Wrapper generation requires Doxygen for header parsing plus a full Python
  runtime in the build environment; the generated C/Fortran bindings are not
  part of the C++ library deliverable
- C++ API (OpenMM.h) is unaffected — all functionality remains available

### Python Wrappers Disabled
- `OPENMM_BUILD_PYTHON_WRAPPERS=OFF`
- Python wrappers require Swig and are Python bindings, not C++ library functionality
- Not applicable for a C++ conan package

### Examples and Tests Disabled
- `OPENMM_BUILD_EXAMPLES=OFF` — demo programs not needed for library package
- `BUILD_TESTING=OFF` — upstream tests not integrated; conan test_package handles testing

## Potential Issues

1. **ELF signing**: OpenMM .so files need to be signed for OHOS execution.
   The CI sign.sh script handles this automatically.

2. **HMDFS limitations**: If the build encounters symlink issues, use `cp` instead
   of `ln -s` (E046/E051 known HMDFS issues).

## Upstream Test Inventory (R51)

Source: `openmm-8.1.2.tar.gz` (sha256 `afc888a4…` verified against GitHub release).
Each `tests/` directory registers one ctest entry per `*Test*.cpp` via
`FILE(GLOB TEST_PROGS "*Test*.cpp")` + `ADD_TEST` (tests/CMakeLists.txt:8-32).

Test programs in scope of this recipe (non-GPU components that are built):

| Component | Test programs |
|---|---|
| Core API (tests/) | 10 |
| Reference platform | 46 |
| CPU platform | 18 |
| Serialization | 33 |
| Amoeba plugin (reference + serialization) | 13 |
| Drude plugin (reference + serialization) | 7 |
| RPMD plugin (reference) | 1 |
| CPU PME plugin | 1 |
| **Total in scope (non-GPU)** | **129** |

GPU-only test programs (not built — CUDA/OpenCL platforms disabled):
core CUDA 46, core OpenCL 47, Amoeba CUDA+OpenCL 14, Drude CUDA+OpenCL 8,
RPMD CUDA+OpenCL 2 — 117 entries excluded from the build.

Upstream suite disposition: the recipe builds with `BUILD_TESTING=OFF`; package
verification is done through the conan `test_package` consumer test
(`test_package/test_openmm.cpp`), which links the installed library, checks
`Platform::getOpenMMVersion() == 8.1.2`, builds a `System` with one particle,
and confirms the Reference and CPU platforms load at runtime (CPU via dlopen
from `lib/plugins/`). Wiring the full 129-entry upstream suite into
`conan create` is not done because the ctest entries execute MD simulation
workloads whose runtime would exceed the CI budget for a consumer-package
gate; the library API surface is exercised by test_package.

## Continuation Session (2026-09-17)

Follow-up on PR #6957 (CI never ran — comment-triggered pipeline):

1. **conandata.yml**: removed `gh-proxy.com` mirror prefix URL (PF7 mirror
   blacklist). Only the official GitHub release URL is declared; the CI
   pipeline auto-injects mirror fallbacks at build time. sha256 unchanged
   (`afc888a4e46486d8d68dac4d403e2b0b28f51b95e52e821e34c38e8b428e040e`,
   re-verified by direct download).
2. **notes.md**: corrected wrapper section (wrappers are OFF, no
   tool_requires), filled SHA256 (was previously listed as uncomputed), added
   upstream test inventory above.
3. **ELF SONAME fix (L5 CI gate + real dlopen bug)**: native OHOS CMake has no
   `Platform/HarmonyOS` module, so `CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG` is
   undefined — upstream's `SOVERSION "8.1"` on libOpenMM was silently ignored,
   producing .so files without `DT_SONAME` (L5a) and plugins whose
   `DT_NEEDED` recorded the build-tree relative path `../../libOpenMM.so`
   (L5b). The relative NEEDED entries also broke runtime `dlopen()` of the
   plugin libraries, so only the built-in Reference platform was reachable.
   Fix: inject `CMAKE_SHARED_LIBRARY_SONAME_C/CXX_FLAG="-Wl,-soname,"` via
   CMakeToolchain in `generate()` (pattern from adwaita-qt/1.4.2). Result:
   libOpenMM.so.8.1 carries SONAME `libOpenMM.so.8.1` (upstream-faithful,
   Linux behaves the same via SOVERSION), plugins record SONAME-based
   DT_NEEDED, and the CPU/Amoeba/Drude/RPMD/PME plugins now load at runtime.
4. **OPENMM_PLUGIN_DIR**: `Platform::getDefaultPluginsDirectory()` hardcodes
   `/usr/local/openmm/lib/plugins`; the recipe now exports
   `OPENMM_PLUGIN_DIR=<package>/lib/plugins` via `runenv_info` so consumers
   can discover the packaged plugins.
5. **test_package strengthened**: now calls
   `Platform::loadPluginsFromDirectory(getDefaultPluginsDirectory())` and
   requires both the Reference and the CPU plugin platform — verifying the
   dlopen plugin path end-to-end (previously only the built-in Reference
   platform was checked).
6. Local `conan create` verification re-run with the ohos-aarch64 profile
   (results recorded in test-report.md).

## W4 Audit Fixes (2026-09-17, same session)

Independent pre-PR audit findings addressed:

1. **conandata.yml re-pollution**: the W3 local CI run's mirror-fallback
   rewrite re-added the gh-proxy prefix and its trap-restore left the file in
   the rewritten state (plus `.ghfast-bak`/`.orig` leftovers). Restored the
   clean single-URL conandata.yml and deleted the backup files. Only the
   official GitHub URL is declared.
2. **OPENMM_BUILD_HIP_LIB removed**: OpenMM 8.1.2 has no HIP platform
   (platforms/: common/cpu/cuda/opencl/reference) — the option was inert dead
   config. Removed from conanfile.py and manifest.yaml; HIP mentions removed
   from notes.
3. **Upstream test inventory corrected**: per-component recount of non-GPU
   `*Test*.cpp` programs gives 129 in scope (previous table over-counted by
   including 24 CUDA/OpenCL plugin tests); the 117 GPU-only programs are now
   listed explicitly as excluded.
4. **conanfile.py url placeholder removed** (`url = ""  # CI fills this` is a
   forbidden template placeholder) — set to the upstream repository.
5. **commands.json removed**: openmm is a pure library package
   (package_type=library, no bin/ artifacts); PF8/R38 requires libraries to
   NOT carry commands.json.
6. **manifest.yaml dates updated** to the 2026-09-17 re-verification build.
---

**编译结束**: 2026-09-17 13:02
**最终状态**: built
