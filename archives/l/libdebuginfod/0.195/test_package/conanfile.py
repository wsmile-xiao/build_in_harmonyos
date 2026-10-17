import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.build import cross_building
from conan.tools.env import VirtualRunEnv


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    generators = "CMakeToolchain", "CMakeDeps"

    def layout(self):
        cmake_layout(self)

    def generate(self):
        VirtualRunEnv(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not cross_building(self):
            bin_path = os.path.join(self.cpp.build.bindir, "test_probe")
            self.run(bin_path, env="conanrun")
            pkg_bindir = self.dependencies[self.tested_reference_str].cpp_info.bindirs[0]
            script = os.path.join(self.source_folder, "test_debuginfod_cli.sh")
            self.run("/bin/sh %s %s" % (script, os.path.join(pkg_bindir, "debuginfod-find")), env="conanrun")
