#!/usr/bin/env python3
"""Conan recipe — corrade 2020.06 (HarmonyOS PC aarch64).

Corrade is the base utility library for the Magnum engine. It builds
multiple independent libraries (Utility/Containers/TestSuite/PluginManager/
Interconnect) with CMake; on OHOS the dynamic plugins must link their
dependencies explicitly (musl loader), which is handled by the patches.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class CorradeConan(ConanFile):
    name = "corrade"
    version = "2020.06"
    description = "Corrade is a multiplatform utility library written in C++11/C++14, used as a base for the Magnum graphics engine"
    license = "MIT"
    homepage = "https://magnum.graphics/corrade"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["CMAKE_BUILD_TYPE"] = "Release"
        # corrade 2020.06 的 CMakeLists 最低要求 < 3.5, 新 CMake 移除旧版策略兼容
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.variables["BUILD_TESTS"] = "ON"
        tc.variables["WITH_INTERCONNECT"] = "ON"
        tc.variables["WITH_PLUGINMANAGER"] = "ON"
        tc.variables["WITH_TESTSUITE"] = "ON"
        tc.variables["WITH_UTILITY"] = "ON"
        tc.variables["WITH_MAIN"] = "ON"
        tc.variables["BUILD_DEPRECATED"] = "ON"
        # 交叉编译时需要宿主 corrade-rc; 若未通过 conf 提供, 由 CMake find_program 自行查找
        rc = self.conf_info.get("user.corrade:rc_path", default="")
        if rc:
            tc.variables["CORRADE_RC_EXECUTABLE"] = rc
        # OHOS 工具链默认 --no-undefined, corrade 动态插件跨库符号需放宽
        tc.extra_flags = "-Wl,-z,undefs"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # Link order matters (reverse dependency order for static linking).
        self.cpp_info.set_property("cmake_file_name", "Corrade")
        self.cpp_info.set_property("cmake_target_name", "Corrade::Corrade")
        self.cpp_info.components["utility"].set_property("cmake_target_name", "Corrade::Utility")
        self.cpp_info.components["utility"].libs = ["CorradeUtility"]
        # Containers 是 header-only, 无独立库文件
        self.cpp_info.components["containers"].set_property("cmake_target_name", "Corrade::Containers")
        self.cpp_info.components["containers"].libs = []
        self.cpp_info.components["testsuite"].set_property("cmake_target_name", "Corrade::TestSuite")
        self.cpp_info.components["testsuite"].libs = ["CorradeTestSuite"]
        self.cpp_info.components["pluginmanager"].set_property("cmake_target_name", "Corrade::PluginManager")
        self.cpp_info.components["pluginmanager"].libs = ["CorradePluginManager"]
        self.cpp_info.components["interconnect"].set_property("cmake_target_name", "Corrade::Interconnect")
        self.cpp_info.components["interconnect"].libs = ["CorradeInterconnect"]
