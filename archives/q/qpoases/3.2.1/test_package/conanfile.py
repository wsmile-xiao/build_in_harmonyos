#!/usr/bin/env python3
"""Consumer test package for qpOASES 3.2.1 (static C++ QP solver)."""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class QpoasesTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def _emulator(self):
        """Cross-compilation emulator injected by the OHOS *-run profile."""
        extra = self.conf.get("tools.cmake.cmaketoolchain:extra_variables",
                              default={}, check_type=dict)
        emu = extra.get("CMAKE_CROSSCOMPILING_EMULATOR")
        if isinstance(emu, (list, tuple)):
            return " ".join(str(e) for e in emu)
        return str(emu) if emu else ""

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["CMAKE_CXX_STANDARD"] = "11"
        if self.settings.os == "OHOS":
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = str(self.settings.arch)
        tc.user_presets_path = False
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        exe = os.path.join(self.cpp.build.bindirs[0], "test_qpoases")
        emu = self._emulator()
        if can_run(self):
            self.run('"%s"' % exe, env="conanrun")
        elif emu:
            # Cross-built for OHOS: execute through the profile's emulator so the
            # consumer end-to-end test really runs instead of being skipped.
            self.run('%s "%s"' % (emu, exe), env="conanrun")
        else:
            raise ConanException(
                "cannot run the consumer test: no native execution and no "
                "CMAKE_CROSSCOMPILING_EMULATOR configured")
