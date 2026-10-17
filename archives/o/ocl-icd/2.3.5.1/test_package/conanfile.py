#!/usr/bin/env python3
"""Conan test_package — ocl-icd 2.3.5

L1 test: links against the built libOpenCL and calls clGetPlatformIDs.
A return of CL_SUCCESS (platforms present) or -1001
(CL_PLATFORM_NOT_FOUND_KHR, no OpenCL driver on the worker) both prove the
loader library is linkable and callable.
"""
import json
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class OclIcdTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # CL headers for the consumer test; the ocl-icd package itself
        # builds against its bundled khronos-headers copy.
        self.requires("opencl-headers/2026.05.29")

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            bin_path = os.path.join(self.cpp.build.bindirs[0],
                                    "test_ocl_icd")
            self.run(bin_path, env="conanrun")
            marker = {
                "executed": True,
                "passed": True,
                "command": bin_path,
                "discovered": 1,
                "passedCount": 1,
            }
            self.output.info("HMBS_TEST_PACKAGE_RESULT="
                             + json.dumps(marker))
