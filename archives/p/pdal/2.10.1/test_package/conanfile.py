#!/usr/bin/env python3
"""Consumer test for pdal."""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.env import Environment


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        # The pdal stack links libc++_shared.so from the platform SDK.  The
        # OHOS loader has no default search path for it, and conanrun only
        # covers conan-managed libdirs, so expose the system directory that
        # carries the C++ runtime explicitly at test time (same approach as
        # archives/a/avahi-ui/0.8/test_package).
        run_env = Environment()
        run_env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        run_env.vars(self).save_script("system_run_env")

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            bin_path = os.path.join(self.cpp.build.bindir, "test_package")
            self.run(bin_path, env=["conanrun", "system_run_env"])
