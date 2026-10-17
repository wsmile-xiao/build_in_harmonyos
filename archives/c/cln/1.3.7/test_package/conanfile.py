import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.build import cross_building


class ClnTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeToolchain", "CMakeDeps", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not cross_building(self):
            # 显式前插被测包 lib 目录：VirtualRunEnv 聚合的 LD_LIBRARY_PATH
            # 在部分环境下缺被测包自身 libdir，动态加载会命中旧库
            cln_dep = self.dependencies[self.tested_reference_str]
            libdir = os.path.join(cln_dep.package_folder, "lib")
            exe = os.path.join(self.cpp.build.bindir, "consumer")
            self.run('export LD_LIBRARY_PATH="%s:$LD_LIBRARY_PATH"; "%s"' % (libdir, exe),
                     env="conanrun")
