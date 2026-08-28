import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain
from conan.tools.env import Environment


class WhereamiTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        CMakeDeps(self).generate()
        CMakeToolchain(self).generate()

    def _build_environment(self):
        environment = Environment()
        if self.settings.os == "OHOS":
            compilers = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict
            )
            compiler = compilers.get("c") or "clang"
            llvm_lib = os.path.join(
                os.path.dirname(os.path.dirname(os.path.realpath(compiler))), "lib"
            )
            if os.path.isfile(os.path.join(llvm_lib, "libxml2.so.16")):
                environment.prepend_path("LD_LIBRARY_PATH", llvm_lib)
        return environment

    def build(self):
        cmake = CMake(self)
        with self._build_environment().vars(self).apply():
            cmake.configure()
            cmake.build()

    def test(self):
        self.run("./whereami_test", env="conanrun")
