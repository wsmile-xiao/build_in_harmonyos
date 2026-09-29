import os
import shlex

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibtracecmdConsumerTest(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
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
        exe = os.path.join(self.build_folder, self.cpp.build.bindirs[0],
                           "libtracecmd_consumer_test")
        # 链接在 conanbuild 下由 cmake.build() 完成，运行才需要 conanrun
        # （libtracecmd.so 与它链的 libz.so 都在包目录里）。
        self.run(shlex.quote(exe), env="conanrun")
