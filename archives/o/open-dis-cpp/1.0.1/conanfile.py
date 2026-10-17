#!/usr/bin/env python3
"""Conan recipe — open-dis-cpp 1.0.1 (CMake)"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class OpenDisCppConan(ConanFile):
    name = "open-dis-cpp"
    version = "1.0.1"
    description = "C++ implementation of the Distributed Interactive Simulation (DIS) protocol (IEEE 1278.1)"
    license = "BSD-2-Clause"
    homepage = "https://github.com/open-dis/open-dis-cpp"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos/tree/main/archives/o/open-dis-cpp/1.0.1"
    topics = ("dis", "ieee-1278", "distributed-simulation", "cpp11")
    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS", "Windows", "Macos", "FreeBSD"):
            raise ConanInvalidConfiguration(
                f"{self.name} supports Linux/OHOS/Windows/Macos/FreeBSD, not {self.settings.os}"
            )

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # 上游三个开关（CMakeLists.txt option()）：库 + 上游测试进构建，示例应用关掉
        tc.cache_variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.cache_variables["BUILD_TESTS"] = "ON"
        tc.cache_variables["BUILD_EXAMPLES"] = "OFF"  # 示例需 SDL2/SDL2_net（上游可选依赖，缺省禁用）
        # 上游 cmake_minimum_required(VERSION 3.2)：CMake 4.x 已移除 <3.5 兼容，
        # 不给该变量 configure 直接失败（设备与 CI 同为 CMake 4.1.2，实测见 notes.md #1）
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        if can_run(self):
            # 上游 Catch2 v2.13.10 单测：ctest 注册 1 个入口，内含 8 个 TEST_CASE
            cmake.test()
        else:
            self.output.info("Cross-building: upstream Catch2 suite was built but not executed")

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # 上游以一个包导出两个互斥协议库（DIS6 / DIS7）：类名大量重叠（92 个同名头文件、
        # 同处 namespace DIS）而内存布局不同，同时链接会互相占位（ODR 风险），
        # 故拆成两个 component，消费者按协议版本二选一。
        self.cpp_info.components["dis6"].libs = ["OpenDIS6"]
        self.cpp_info.components["dis6"].set_property("cmake_target_name", "open-dis-cpp::dis6")

        self.cpp_info.components["dis7"].libs = ["OpenDIS7"]
        self.cpp_info.components["dis7"].set_property("cmake_target_name", "open-dis-cpp::dis7")
