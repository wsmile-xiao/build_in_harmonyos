import os
from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment, VirtualRunEnv

class ChromaprintTest(ConanFile):
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
        temporary = os.path.join(self.build_folder, "consumer-tmp")
        os.makedirs(temporary, exist_ok=True)
        environment = Environment()
        environment.define("TMPDIR", temporary)
        environment.define("LC_ALL", "C")
        with environment.vars(self).apply():
            executable = os.path.join(self.cpp.build.bindirs[0], "test_chromaprint")
            self.run(executable, env="conanrun")
