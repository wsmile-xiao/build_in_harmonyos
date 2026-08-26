#!/usr/bin/env python3
"""test_package/conanfile.py — mitama-cpp-result 11.0.0 consumer test."""
import os

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class MitamaCppResultTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        # os=OHOS 守卫：对齐 cmake 的 Modules/Platform/OHOS.cmake，
        # 避免 conan 默认的 "HarmonyOS" 导致平台变量留空（与 fmt/12.2.0 一致）。
        if self.settings.os == "OHOS":
            tc.blocks["generic_system"].values["cmake_system_name"] = "OHOS"
            tc.blocks["generic_system"].values["cmake_system_processor"] = "aarch64"
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if cross_building(self):
            self.output.info("cross-building: 只验编译+链接")
            return
        # 显式拼 LD_LIBRARY_PATH：fmt/12.2.0 默认 shared，VirtualRunEnv 的
        # conanrunenv 不总可靠（见 fmt 12.2.0 notes），需显式拼依赖 libdirs。
        libdirs = []
        for _ref, _d in self.dependencies.items():
            libdirs += _d.cpp_info.libdirs
        ldpath = os.pathsep.join(dict.fromkeys(libdirs))
        bash = os.environ.get("CONFIG_SHELL", "bash")
        self.run(
            f'{bash} -c \'export LD_LIBRARY_PATH="{ldpath}'
            f'${{LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}}"; ./test_package\'',
            env="conanrun",
        )
