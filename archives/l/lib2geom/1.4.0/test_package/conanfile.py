import os
from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, CMakeDeps, cmake_layout
from conan.tools.env import Environment, VirtualRunEnv


class Lib2GeomTest(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeToolchain(self).generate()
        CMakeDeps(self).generate()
        VirtualRunEnv(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            return
        tmp = os.path.join(self.build_folder, "consumer-tmp")
        os.makedirs(tmp, exist_ok=True)
        env = Environment()
        env.define("TMPDIR", tmp)
        with env.vars(self).apply():
            self.run(os.path.join(self.cpp.build.bindirs[0], "test_geom"), env="conanrun")
