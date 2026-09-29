#!/usr/bin/env python3
"""Consumer test for installkernel/4.1."""

import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class InstallkernelTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeToolchain(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        dep = self.dependencies["installkernel"]
        root = dep.package_folder
        sbin = os.path.join(root, dep.cpp_info.bindirs[0])
        if not os.path.isdir(sbin):
            raise Exception(f"installkernel sbin dir not found: {sbin}")
        if not can_run(self):
            self.output.info("Cross-built installkernel_probe; runtime "
                             "verification is deferred to the OHOS target")
            return
        probe = os.path.join(self.cpp.build.bindir, "installkernel_probe")
        self.run(f'"{probe}" "{root}"', env="conanrun")
