#!/usr/bin/env python3
"""Conan recipe — libclsph 2.6 (OpenCL SPH simulation library).

Adaptation notes (HarmonyOS PC, arm64):
  * Upstream is CMake-based (NOT autotools); builds static library `clsph`.
  * Upstream requires OpenCL. OHOS has no system CL headers/lib and the PC has
    no GPU OpenCL driver, so the recipe supplies:
      - requires("ocl-icd/2.3.5")         -> libOpenCL.so (ICD loader)
      - conandata `cl_headers` source     -> official Khronos OpenCL C headers
  * The library vendors its own OpenCL C++ bindings (util/cl.hpp) selected via
    -DUSE_LOCAL_CL_HPP; a patch adds the missing enqueueFillBuffer (OpenCL 1.2).
  * cmake_minimum_required is patched 2.6 -> 3.5 (CMake >= 4 dropped < 3.5).
  * BUILD_EXAMPLES=OFF: opengl example needs GLFW/OpenGL (absent on OHOS); the
    particles example is demonstrably buildable/runnable (see reports/ ledger).
  * Runtime data (kernels/, scenes/, fluid_properties/, simulation_properties/,
    shaders/, common/) is packaged under share/libclsph/ because the upstream
    code reads kernels/data relative to CWD at run time.
"""
import glob
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy


class LibclsphConan(ConanFile):
    name = "libclsph"
    version = "2.6"
    description = "OpenCL based GPU accelerated SPH fluid simulation library"
    license = "MIT"
    homepage = "https://github.com/libclsph/libclsph"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # OpenCL ICD loader — provides libOpenCL.so for link + runtime.
        self.requires("ocl-icd/2.3.5")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"libclsph only supports Linux/OHOS, got: {self.settings.os}")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # Official Khronos OpenCL C headers (CL/cl.h etc.) for the OHOS build.
        get(self, **self.conan_data["cl_headers"], strip_root=True,
            destination="cl_headers")

    def generate(self):
        tc = CMakeToolchain(self)
        ocl = self.dependencies["ocl-icd"]
        ocl_lib = sorted(glob.glob(os.path.join(ocl.package_folder, "lib", "libOpenCL.so*")))[0]
        clhdr = os.path.join(self.source_folder, "cl_headers")
        tc.variables["OPENCL_INCLUDE_DIRS"] = clhdr
        tc.variables["OPENCL_LIBRARIES"] = ocl_lib
        tc.variables["BUILD_EXAMPLES"] = "OFF"
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # Use the library's vendored OpenCL C++ bindings (patched cl.hpp).
        tc.preprocessor_definitions["USE_LOCAL_CL_HPP"] = "1"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        # Headers: the project copies its public headers into the build dir.
        inc = os.path.join(self.build_folder, "include", "clsph")
        copy(self, "*.h", src=inc, dst=os.path.join(self.package_folder, "include", "clsph"))
        copy(self, "*", src=os.path.join(inc, "common"),
             dst=os.path.join(self.package_folder, "include", "clsph", "common"))
        copy(self, "*", src=os.path.join(inc, "util"),
             dst=os.path.join(self.package_folder, "include", "clsph", "util"))
        copy(self, "*", src=os.path.join(inc, "file_save_delegates"),
             dst=os.path.join(self.package_folder, "include", "clsph", "file_save_delegates"))
        # OpenCL C headers (Khronos, official) — the vendored cl.hpp shipped
        # in clsph/util requires <CL/opencl.h> at consumer compile time.
        copy(self, "*", src=os.path.join(self.source_folder, "cl_headers", "CL"),
             dst=os.path.join(self.package_folder, "include", "CL"))
        # Library
        copy(self, "*.a", src=os.path.join(self.build_folder, "lib"),
             dst=os.path.join(self.package_folder, "lib"))
        # Runtime data (kernel sources, scenes, properties, shaders) — the
        # upstream code resolves these relative to CWD at run time.
        data = os.path.join(self.package_folder, "share", "libclsph")
        for d in ("kernels", "scenes", "fluid_properties",
                  "simulation_properties", "shaders", "common"):
            src = os.path.join(self.build_folder, "examples", d)
            if os.path.isdir(src):
                copy(self, "*", src=src, dst=os.path.join(data, d))
        # License
        copy(self, "license.txt", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["clsph"]
        # headers live under include/clsph; the project's internal relative
        # includes ("common/structures.h", "util/cl_boilerplate.h") resolve
        # against include/clsph, so expose it as an extra include dir.
        self.cpp_info.includedirs = ["include", "include/clsph"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.requires = ["ocl-icd::ocl-icd"]