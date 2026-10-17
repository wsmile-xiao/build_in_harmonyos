#!/usr/bin/env python3
"""Conan test package for caf 1.1.0."""

import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualRunEnv
from conan.tools.files import save


class TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()

        tc = CMakeToolchain(self)
        if self.settings.os == "OHOS":
            rules = os.path.join(
                self.generators_folder, "ohos-cmake-rules.cmake"
            )
            save(
                self,
                rules,
                "\n".join(
                    (
                        'set(CMAKE_SHARED_LIBRARY_SONAME_C_FLAG "-Wl,-soname,")',
                        'set(CMAKE_SHARED_LIBRARY_RUNTIME_C_FLAG "-Wl,-rpath,")',
                        'set(CMAKE_SHARED_LIBRARY_RUNTIME_C_FLAG_SEP ":")',
                        'set(CMAKE_SHARED_LIBRARY_RPATH_LINK_C_FLAG "-Wl,-rpath-link,")',
                        'set(CMAKE_SHARED_LIBRARY_RPATH_ORIGIN_TOKEN "$ORIGIN")',
                    )
                )
                + "\n",
            )
            tc.cache_variables["CMAKE_USER_MAKE_RULES_OVERRIDE_C"] = rules
            tc.cache_variables["CMAKE_BUILD_RPATH"] = ";".join(
                self.dependencies["caf"].cpp_info.libdirs
            )
        tc.generate()
        VirtualRunEnv(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            self.output.info("cross-building: caf consumer linked but cannot run")
            return
        test_exe = os.path.join(self.cpp.build.bindirs[0], "test_caf")
        if not os.path.isfile(test_exe):
            raise ConanException(f"test executable not found: {test_exe}")
        self.run(test_exe, env="conanrun")
