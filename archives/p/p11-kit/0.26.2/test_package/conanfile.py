import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class P11KitTestPackage(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        CMakeToolchain(self).generate()

    def build(self):
        self._prepare_build_environment()
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            self.run(
                os.path.join(self.cpp.build.bindir, "test_package"),
                env="conanrun",
            )

    def _prepare_build_environment(self):
        if self.settings.os != "OHOS":
            return

        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        compiler = compilers.get("c")
        if not compiler:
            raise ConanException(
                "tools.build:compiler_executables must define the C compiler"
            )
        compiler = os.path.realpath(compiler)
        llvm_lib = os.path.join(os.path.dirname(os.path.dirname(compiler)), "lib")
        if not os.path.isfile(os.path.join(llvm_lib, "libxml2.so.16")):
            raise ConanException(
                "OHOS SDK libxml2.so.16 not found beside compiler: {}".format(
                    llvm_lib
                )
            )

        current_ld_path = os.environ.get("LD_LIBRARY_PATH", "")
        os.environ["LD_LIBRARY_PATH"] = os.pathsep.join(
            path for path in (llvm_lib, current_ld_path) if path
        )
