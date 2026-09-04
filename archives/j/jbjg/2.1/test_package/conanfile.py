import os
from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.build import cross_building


class JbjgTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeToolchain", "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if cross_building(self):
            self.output.info("cross-building：只验编译+链接")
            return
        # Use the configured target shell explicitly when launching the real test ELF.
        # The static package has no shared-library runtime path requirement.
        shell = os.environ.get("CONFIG_SHELL", "/system/bin/sh")
        test_bin = os.path.join(self.cpp.build.bindir, "test_jbjg")
        self.run("{} -c '{}'".format(shell, test_bin), env="conanrun")
