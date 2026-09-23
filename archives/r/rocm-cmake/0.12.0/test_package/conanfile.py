import os
from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.env import Environment

class RocmCMakeTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        env = Environment()
        pkg_folder = self.dependencies[self.tested_reference_str].package_folder
        rocm_dir = os.path.join(pkg_folder, "share", "rocm", "cmake")
        env.define("ROCM_DIR", rocm_dir)
        envvars = env.vars(self)
        envvars.save_script("conanbuildenv")

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def layout(self):
        cmake_layout(self)

    def test(self):
        if can_run(self):
            cmd = os.path.join(self.cpp.build.bindir, "test_package")
            self.run(cmd, env="conanrun")
