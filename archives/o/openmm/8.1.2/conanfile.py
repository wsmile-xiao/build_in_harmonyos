#!/usr/bin/env python3
"""Conan recipe for OpenMM 8.1.2 — High-performance toolkit for molecular simulation.

OpenMM is a toolkit for molecular simulation using high performance GPU code.
It can be used either as a stand-alone application for running simulations,
or as a library for calling simulation routines directly from other code.

Build system: CMake (minimum 3.17)
Source: https://github.com/openmm/openmm

Key adaptation points for OHOS aarch64:
  - GPU platforms (CUDA/OpenCL) disabled — no GPU SDK on OHOS PC
  - CPU platform kept (optimized for aarch64 with asmjit JIT)
  - All plugins kept (Amoeba, RPMD, Drude, CPU PME)
  - C and Fortran wrappers disabled (requires Doxygen for header parsing)
  - Python wrappers disabled (requires Swig, not applicable for C++ library)
  - ELF DT_SONAME injected on OHOS (no Platform/HarmonyOS CMake module)
  - Patch: CMake CMP0042 policy fixed for CMake 4.x compatibility
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class OpenmmConan(ConanFile):
    name = "openmm"
    version = "8.1.2"
    description = "High-performance toolkit for molecular simulation"
    license = "LGPL-3.0-or-later"
    homepage = "https://openmm.org/"
    url = "https://github.com/openmm/openmm"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
    }
    default_options = {
        "shared": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # OpenMM has no external Conan dependencies — all internal libraries
        # (jama, quern, lepton, sfmt, lbfgs, hilbert, csha1, pocketfft, vkfft,
        # irrxml, asmjit) are bundled in the source tree.
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # R26: OpenMM is not a system-name library, shared is fine
        tc.variables["OPENMM_BUILD_SHARED_LIB"] = "ON" if self.options.shared else "OFF"
        tc.variables["OPENMM_BUILD_STATIC_LIB"] = "OFF" if self.options.shared else "ON"

        # OHOS: CMake has no Platform/HarmonyOS module, so
        # CMAKE_SHARED_LIBRARY_SONAME_<LANG>_FLAG stays undefined and shared
        # libraries would ship without DT_SONAME. Worse, OpenMM's plugins link
        # the build-tree path "../../libOpenMM.so", which lld records verbatim
        # as DT_NEEDED — the loader then cannot resolve the dependency at
        # dlopen time and no plugin platform can be loaded. Defining the
        # standard ELF SONAME flag makes the linker emit DT_SONAME for every
        # library and lets it substitute the SONAME for path-style DT_NEEDED
        # entries (same pattern as adwaita-qt/1.4.2).
        if self.settings.os == "OHOS":
            for language in ("C", "CXX"):
                tc.variables[f"CMAKE_SHARED_LIBRARY_SONAME_{language}_FLAG"] = (
                    "-Wl,-soname,"
                )

        # Disable GPU platforms — no CUDA/OpenCL SDK on OHOS PC
        # (OpenMM 8.1.2 ships CUDA and OpenCL platforms only; no HIP)
        tc.variables["OPENMM_BUILD_CUDA_LIB"] = "OFF"
        tc.variables["OPENMM_BUILD_OPENCL_LIB"] = "OFF"

        # Keep CPU platform (optimized for aarch64)
        tc.variables["OPENMM_BUILD_CPU_LIB"] = "ON"

        # Keep all plugins
        tc.variables["OPENMM_BUILD_AMOEBA_PLUGIN"] = "ON"
        tc.variables["OPENMM_BUILD_RPMD_PLUGIN"] = "ON"
        tc.variables["OPENMM_BUILD_DRUDE_PLUGIN"] = "ON"
        tc.variables["OPENMM_BUILD_PME_PLUGIN"] = "ON"

        # C and Fortran wrappers disabled — requires Doxygen for header parsing
        # which is not available in the OHOS build environment
        tc.variables["OPENMM_BUILD_C_AND_FORTRAN_WRAPPERS"] = "OFF"

        # Disable Python wrappers (requires Swig, not applicable for C++ library)
        tc.variables["OPENMM_BUILD_PYTHON_WRAPPERS"] = "OFF"

        # Disable examples and upstream tests (conan test_package handles testing)
        tc.variables["OPENMM_BUILD_EXAMPLES"] = "OFF"
        tc.variables["BUILD_TESTING"] = "OFF"

        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["OpenMM"]
        # OpenMM plugins are loaded at runtime via dlopen, not linked directly
        # Plugin directories: lib/plugins/ (Amoeba, RPMD, Drude, CPUPME)
        # Platform libraries: lib/ (CPU, Reference)
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.includedirs = ["include"]
        # Platform::getDefaultPluginsDirectory() falls back to a hardcoded
        # /usr/local/openmm/lib/plugins; export OPENMM_PLUGIN_DIR so consumers
        # that call loadPluginsFromDirectory() find the packaged plugins.
        self.runenv_info.define(
            "OPENMM_PLUGIN_DIR", os.path.join(self.package_folder, "lib", "plugins"))
