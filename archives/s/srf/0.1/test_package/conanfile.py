#!/usr/bin/env python3
"""Conan test_package for srf 0.1.

R34: real consumer test — test_srf_ztr.cc exercises the libsrf API
(SRF_create_read/SRF_output_ztr/SRF_Container/SRF_ReadSet/SRF_Read)
exactly as upstream test/testWrite.cc + test/testRead.cc do, through a
real SRF file round-trip.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class SrfTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # srf is a static archive built against io_lib; the consumer
        # links both (io_lib cpp_info propagates libstaden-read deps)
        self.requires("io_lib/1.14.9")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        env = Environment()
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                env.prepend_path("LD_LIBRARY_PATH",
                                 os.path.join(dep.package_folder, "lib"))
        env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        # test reads its inputs from cwd: run from the test source
        # folder so the sample data is present; binary path must be
        # absolute (bindirs may be relative and would break after cd)
        exe = os.path.abspath(os.path.join(self.cpp.build.bindirs[0],
                                           "test_srf_ztr"))
        with env.vars(self).apply():
            self.run("cd %s && %s" % (self.source_folder, exe))
