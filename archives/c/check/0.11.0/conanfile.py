#!/usr/bin/env python3
"""Conan recipe — check 0.11.0 (CMake).

Check is a unit testing framework for C. This version is built with the
upstream CMake build system (autotools also ships, but CMake avoids the
config.status OHOS quirks; same approach as the archived 0.15.2 recipe).
"""
from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, cmake_layout, CMakeToolchain
from conan.tools.env import VirtualBuildEnv
import os

required_conan_version = ">=2.0"


class CheckConan(ConanFile):
    name = "check"
    version = "0.11.0"
    package_type = "library"

    description = "A unit testing framework for C"
    homepage = "https://libcheck.github.io/check/"
    license = "LGPL-2.1-only"
    url = "https://github.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        venv = VirtualBuildEnv(self)
        venv.generate()

        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = self.options.shared
        tc.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = self.options.get_safe("fPIC", True)
        # check 0.11.0 上游声明 cmake_minimum_required(2.8)，新版 CMake(>=3.5)
        # 已移除旧版兼容，必须显式声明最小策略版本才能配置成功。
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE*", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        # check 上游许可证文件名为 COPYING.LESSER，一并拷贝
        copy(self, "COPYING*", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "check")
        self.cpp_info.set_property("cmake_target_name", "Check::check")
        self.cpp_info.libs = ["check"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.system_libs = ["m", "rt", "pthread"]
