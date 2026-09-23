#!/usr/bin/env python3
"""Conan test_package — platform_folders 4.2.0."""
import os

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualRunEnv


class PlatformFoldersTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        # 与主配方一致的 generic_system 映射（R32 OHOS）
        if self.settings.os in ("Linux", "OHOS"):
            tc.blocks["generic_system"].values["cmake_system_name"] = str(self.settings.os)
            if self.settings.os == "OHOS":
                tc.blocks["generic_system"].values["cmake_system_processor"] = "aarch64"
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.generate()
        VirtualRunEnv(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # 本仓 OHOS profile 为原生（build=host），直接跑设备；保留跨编译守卫
        if cross_building(self):
            self.output.info("cross-building: consumer runtime test not executable")
            return
        test_exe = os.path.join(self.cpp.build.bindirs[0], "test_platform_folders")
        if not os.path.isfile(test_exe):
            raise Exception("Test binary not found: %s" % test_exe)
        self.run('"%s"' % test_exe, env="conanrun")
