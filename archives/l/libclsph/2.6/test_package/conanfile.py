#!/usr/bin/env python3
"""test_package for libclsph 2.6 — consumer + HarmonyOS-specific tests.

CI runs these automatically via `conan create` (which invokes test_package).

Runtime notes:
  * OHOS PC has no GPU OpenCL driver, so the tests use the oclgrind software
    OpenCL backend as the platform provider. oclgrind/26.03.1 is a TEST-only
    requirement; the recipe itself only requires the ocl-icd ICD loader.
  * The upstream library resolves its runtime data (kernels/, scenes/,
    fluid_properties/, simulation_properties/) relative to CWD, so the tests
    run from a working directory seeded with the packaged share/libclsph data.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibclsphTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # Software OpenCL backend for the OHOS runtime tests (no GPU OpenCL).
        self.requires("oclgrind/26.03.1")

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # Seed the working directory with the packaged runtime data.
        lib = self.dependencies["libclsph"]
        data_src = os.path.join(lib.package_folder, "share", "libclsph")
        work = str(self.build_folder)
        if os.path.isdir(data_src):
            for d in ("kernels", "scenes", "fluid_properties",
                      "simulation_properties", "shaders", "common"):
                src = os.path.join(data_src, d)
                if os.path.isdir(src):
                    shutil.copytree(src, os.path.join(work, d), dirs_exist_ok=True)

        # Configure the software OpenCL platform via an ICD vendor file.
        oclgrind = self.dependencies["oclgrind"]
        icd_lib = None
        for root, _dirs, files in os.walk(oclgrind.package_folder):
            if "liboclgrind-rt-icd.so" in files:
                icd_lib = os.path.join(root, "liboclgrind-rt-icd.so")
                break
        if icd_lib is None:
            raise RuntimeError("oclgrind ICD library not found in package")
        vendors = os.path.join(work, "oclgrind-vendors")
        os.makedirs(vendors, exist_ok=True)
        with open(os.path.join(vendors, "liboclgrind.icd"), "w") as f:
            f.write(icd_lib + "\n")

        bin_dir = os.path.join(self.cpp.build.bindirs[0])
        for exe in ("consumer_clsph", "ohos_sph_test"):
            self.run(f'OCL_ICD_VENDORS="{vendors}" "{os.path.join(bin_dir, exe)}"',
                     env="conanrun", cwd=work)
