import os
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain


class LibcextTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _compiler_executable(self, key, fallback_name):
        executables = self.conf.get(
            "tools.build:compiler_executables",
            default={},
            check_type=dict,
        ) or {}
        configured = executables.get(key)
        if configured and os.path.isfile(configured):
            return configured
        found = shutil.which(fallback_name)
        return found or configured or fallback_name

    def generate(self):
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        # The shared profile may point tools.build:compiler_executables at a
        # path that does not exist on every worker. When the configured
        # compiler is absent, override it with a real OHOS clang resolved from
        # PATH so CMake can configure. This is a runtime environment fix and
        # does not hardcode any path.
        if str(self.settings.os) == "OHOS":
            cc = self._compiler_executable("c", "clang")
            cxx = self._compiler_executable("cpp", "clang++")
            tc.variables["CMAKE_C_COMPILER"] = cc
            tc.variables["CMAKE_CXX_COMPILER"] = cxx
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        self.run("./test_cext", env="conanrun")
