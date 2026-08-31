#!/usr/bin/env python3
"""Conan recipe template — CMake projects.

Usage: Replace Bambootracker, bambootracker, 0.6.5, bambootracker 0.6.5, MIT, 
       Fill in requires() and cpp_info.libs as needed.

This template enforces R26: BUILD_SHARED_LIBS=OFF for system-name libraries.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class BambootrackerConan(ConanFile):
    name = "bambootracker"
    version = "0.6.5"
    description = "bambootracker 0.6.5"
    license = "MIT"
    homepage = ""
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("qtbase/6.11.1")
        self.requires("qt5compat/6.11.1")
        self.requires("qttools/6.11.1")
        self.requires("alsa-lib/1.2.16")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # R26: System-name libraries default to static
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # Add project-specific CMake variables here:
        # tc.variables["ENABLE_FOO"] = "ON"
        tc.variables["CMAKE_FIND_PACKAGE_PREFER_CONFIG"] = "ON"
        tc.variables["WARNINGS_ARE_ERRORS"] = "OFF"
        # emu2149 子模块声明 cmake_minimum_required(2.8)，CMake 4.x 已移除 <3.5 支持
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # 各 Qt6 包前缀：qtbase 提供 Qt6Config，qt5compat 提供 Core5Compat，
        # qttools 提供 Qt6LinguistTools，alsa 提供 ALSA::asound
        try:
            qtbase = self.dependencies["qtbase"].package_folder
            qt5compat = self.dependencies["qt5compat"].package_folder
            qttools = self.dependencies["qttools"].package_folder
            alsa = self.dependencies["alsa-lib"].package_folder
            tc.cache_variables["CMAKE_PREFIX_PATH"] = ";".join(
                p.replace("\\", "/") for p in (qtbase, qt5compat, qttools, alsa)
            )
            # Qt6Config 的组件搜索受 PATHS 限定在 qtbase 前缀，需显式给出
            # LinguistTools(qttools)/Core5Compat(qt5compat) 组件目录
            tc.cache_variables["Qt6LinguistTools_DIR"] = (
                f"{qttools}/lib/cmake/Qt6LinguistTools"
            ).replace("\\", "/")
            tc.cache_variables["Qt6Core5Compat_DIR"] = (
                f"{qt5compat}/lib/cmake/Qt6Core5Compat"
            ).replace("\\", "/")
        except Exception:
            pass
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        # Qt6 工具(lrelease 等)运行期需要 qtbase 动态库,显式供给其 lib 目录
        env = Environment()
        env.append_path(
            "LD_LIBRARY_PATH",
            str(self.dependencies["qtbase"].package_folder) + "/lib",
        )
        with env.vars(self).apply():
            cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # BambooTracker 是纯可执行包（GUI/Qt6），无 lib/ 产物，不声明库。
        # 声明不存在的 lib 会让 CMakeDeps 生成指向缺失库的 target，
        # 导致 test_package find_package 报 "Library not found"（G2 E225）。
        pass
