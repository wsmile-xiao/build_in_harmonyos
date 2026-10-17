import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class LibpqxxTestPackage(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        toolchain = CMakeToolchain(self)
        if str(self.settings.os) == "OHOS":
            toolchain.blocks["generic_system"].values["cmake_system_name"] = "OHOS"
            toolchain.blocks["generic_system"].values["cmake_system_processor"] = (
                "aarch64" if str(self.settings.arch) == "armv8" else str(self.settings.arch)
            )
        # libpqxx 8.x is a C++20 library; the shared OHOS profile pins 17.
        toolchain.cache_variables["CMAKE_CXX_STANDARD"] = 20
        toolchain.cache_variables["CMAKE_CXX_STANDARD_REQUIRED"] = True
        toolchain.generate()
        CMakeDeps(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            # OHOS consumers link against the platform libc++_shared.so which
            # lives in /system/lib64.  Pin the loader path explicitly so the
            # test binary stays runnable even when the ambient
            # LD_LIBRARY_PATH is malformed on the host shell (same
            # treatment as date/3.0.5 in this repository).
            test_env = Environment()
            test_env.define("LD_LIBRARY_PATH", "/system/lib64")
            with test_env.vars(self).apply():
                self.run(
                    os.path.join(
                        self.cpp.build.bindirs[0], "test_package"
                    ),
                    env="conanrun",
                )
