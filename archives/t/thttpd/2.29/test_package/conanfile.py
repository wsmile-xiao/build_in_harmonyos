import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.build import can_run


class ThttpdTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # R34: exercise the actual binaries from the package.
        # 1) direct exit-code check of the packaged server binary
        # 2) run the compiled test program, which itself locates and
        #    executes thttpd via PATH (conanrun env) and verifies its
        #    version output (see test_package/test.c)
        if can_run(self):
            self.run("thttpd -V", env="conanrun")
            exe = os.path.join(self.build_folder, "test_thttpd")
            self.run(f'"{exe}"', env="conanrun")
