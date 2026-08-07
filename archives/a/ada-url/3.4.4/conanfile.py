#!/usr/bin/env python3
"""Conan recipe — ada-url 3.4.4 (CMake).

WHATWG URL parser C++20 library. Zero dependencies, self-contained.
"""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, copy, apply_conandata_patches
import os

required_conan_version = ">=2.0"


class AdaConan(ConanFile):
    name = "ada-url"
    version = "3.4.4"
    package_type = "library"

    description = "WHATWG URL parser (C++20, zero dependencies)"
    homepage = "https://github.com/ada-url/ada"
    license = "MIT"
    url = "https://github.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    exports_sources = "patches/*"

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["CMAKE_CXX_STANDARD"] = "20"
        tc.variables["CMAKE_CXX_STANDARD_REQUIRED"] = "ON"
        # 上游测试已在 OHOS 真机实测 201/201（见 PR_DESCRIPTION）；
        # CI Worker 无法访问 GitHub（CPM 拉 gtest 失败），故 OFF
        tc.variables["ADA_TESTING"] = "OFF"
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # OHOS 沙箱 git 权限限制，FetchContent 下载 gtest 前设置 safe.directory
        # CI 环境可能已设 safe.directory=*；用 --add 追加（重复设置报错），失败可忽略
        self.run(f'git config --global --add safe.directory "{self.build_folder}"', ignore_errors=True)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE-*", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "ada-url")
        self.cpp_info.set_property("cmake_target_name", "ada-url::ada-url")
        self.cpp_info.libs = ["ada"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]