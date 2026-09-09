#!/usr/bin/env python3
"""Conan recipe — clpeak 1.1.5 (CMake, OpenCL benchmark CLI)

clpeak is a CMake C++11 CLI tool that profiles OpenCL devices to find their
peak capacities (https://github.com/krrishnarraj/clpeak). It builds a single
`clpeak` executable linked against libOpenCL (the ICD loader).

HarmonyOS adaptation notes:
- clpeak's CMakeLists runs `find_package(OpenCL)` + `FIND_PATH(HPP_FOUND
  CL/opencl.hpp ...)`. OpenCL headers (CL/cl.h) come from the ohpcd
  opencl-headers package; libOpenCL.so comes from opencl-icd-loader.
- The C++ binding header CL/opencl.hpp is NOT shipped by the opencl-headers
  package (it only installs *.h), and ohpcd has no opencl-clhpp package, so
  the Khronos OpenCL-CLHPP tarball is vendored in source() (same pattern as
  the clinfo recipe vendoring OpenCL-Headers/ICD-Loader) and its
  include/CL/opencl.hpp is placed next to the CL/cl.h headers in the merged
  include dir we feed CMake via OpenCL_INCLUDE_DIR/OpenCL_LIBRARY cache vars
  (CMake's stock FindOpenCL module reads those two variables; clblast recipe
  precedent).
- OHOS has no system libOpenCL at runtime either; the consumer links the
  opencl-icd-loader package which provides libOpenCL.so. On the preflight
  machine there is no OpenCL ICD/platform driver, so running clpeak prints
  "no platforms found" and exits 0 (verified locally); the single upstream
  CTest entry (clpeak_test_run) therefore passes without a real device.
- package_type = application: only bin/clpeak (+ LICENSE) is installed, no
  libraries for consumers.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class ClpeakConan(ConanFile):
    name = "clpeak"
    version = "1.1.5"
    description = "A tool which profiles OpenCL devices to find their peak capacities"
    license = "Apache-2.0"
    homepage = "https://github.com/krrishnarraj/clpeak"
    url = "https://github.com/krrishnarraj/clpeak"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # OpenCL headers (header-only) + ICD loader (libOpenCL.so)
        self.requires("opencl-headers/2026.05.29")
        self.requires("opencl-icd-loader/v2024.05.08")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"]["clpeak"], strip_root=True)
        # Vendor the Khronos C++ binding header CL/opencl.hpp (the opencl-headers
        # package ships only *.h; clpeak's include/common.h needs <CL/opencl.hpp>).
        get(self, **self.conan_data["sources"]["opencl_clhpp"],
            strip_root=True, destination="OpenCL-CLHPP")

    def generate(self):
        tc = CMakeToolchain(self)
        # Merge opencl-headers CL/*.h + vendored CLHPP CL/opencl.hpp into one
        # include dir, then feed it to CMake's stock FindOpenCL module cache
        # vars (OpenCL_INCLUDE_DIR / OpenCL_LIBRARY), mirroring the clblast
        # recipe's OPENCL_INCLUDE_DIRS/OPENCL_LIBRARIES approach.
        headers = self.dependencies["opencl-headers"].package_folder
        loader = self.dependencies["opencl-icd-loader"].package_folder
        merged = os.path.join(self.build_folder, "opencl-include")
        os.makedirs(os.path.join(merged, "CL"), exist_ok=True)
        hdr_src = os.path.join(headers, "include", "CL")
        if os.path.isdir(hdr_src):
            for f in os.listdir(hdr_src):
                if f.endswith(".h"):
                    shutil.copy2(os.path.join(hdr_src, f), os.path.join(merged, "CL", f))
        clhpp_src = os.path.join(self.source_folder, "OpenCL-CLHPP", "include", "CL")
        for f in ("opencl.hpp", "cl2.hpp"):
            src = os.path.join(clhpp_src, f)
            if os.path.isfile(src):
                shutil.copy2(src, os.path.join(merged, "CL", f))
        tc.variables["OpenCL_INCLUDE_DIR"] = merged
        tc.variables["OpenCL_LIBRARY"] = os.path.join(loader, "lib", "libOpenCL.so")
        # Accept the old CMake of the upstream project
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # Upstream registers one CTest entry (clpeak_test_run) which just runs
        # the clpeak binary; with no OpenCL platform it prints "no platforms
        # found" and exits 0, so the test passes on the preflight machine.
        cmake.test()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # application: no consumer cpp_info
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
