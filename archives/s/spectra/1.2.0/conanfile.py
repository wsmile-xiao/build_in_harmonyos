#!/usr/bin/env python3
"""Conan recipe — spectra 1.2.0 (CMake header-only library).

spectra is a header-only C++ library for large-scale eigenvalue problems,
built on top of Eigen. It uses CMake with INTERFACE library target.
Eigen is auto-downloaded by CPM.cmake during configure step and bundled
into the package (eigen/3.4.0 is not in the Conan registry).
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy, save
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class SpectraConan(ConanFile):
    name = "spectra"
    version = "1.2.0"
    description = "Header-only C++ library for large-scale eigenvalue problems, based on Eigen"
    license = "MPL-2.0"
    homepage = "https://github.com/yixuan/spectra"
    url = ""  # CI fills this
    package_type = "header-library"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def build_requirements(self):
        self.test_requires("catch2/2.13.10-r0")

    def layout(self):
        cmake_layout(self)

    def package_id(self):
        # header-only 库：package_id 不依赖编译器/构建类型/架构
        self.info.clear()

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()

        tc = CMakeToolchain(self)
        # E092: CMake does not recognize OHOS as a target platform
        if self.settings.os in ("Linux", "OHOS"):
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = str(self.settings.arch)
        tc.cache_variables["BUILD_TESTS"] = "ON"
        tc.cache_variables["BUILD_EXAMPLES"] = "OFF"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        catch_hpp = os.path.join(self.source_folder, "test", "catch.hpp")
        if os.path.exists(catch_hpp):
            save(self, catch_hpp, "#include <catch2/catch.hpp>\n")
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        self.run("ctest --output-on-failure", cwd=self.build_folder)

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # 将 CPM.cmake 下载的 Eigen 头文件一并打包
        # (eigen/3.4.0 不在 Conan 注册表中，无法通过 self.requires 引用)
        eigen_source_dir = self._find_eigen_source()
        if not eigen_source_dir:
            raise ConanInvalidConfiguration(
                "Eigen source directory not found; CPM.cmake may have failed to download Eigen"
            )
        eigen_dst = os.path.join(self.package_folder, "include", "eigen3")
        copy(self, "Eigen/*", eigen_source_dir, eigen_dst)
        copy(self, "unsupported/*", eigen_source_dir, eigen_dst)

    def _find_eigen_source(self):
        """定位 CPM.cmake 下载的 Eigen 源码目录。"""
        # 优先从 CMake 缓存读取 Eigen3_SOURCE_DIR
        cache_file = os.path.join(self.build_folder, "CMakeCache.txt")
        if os.path.exists(cache_file):
            with open(cache_file, "r") as f:
                for line in f:
                    if line.startswith("Eigen3_SOURCE_DIR"):
                        path = line.split("=", 1)[1].strip().strip('"')
                        if os.path.isdir(path):
                            return path
        # 回退: 搜索 _deps 目录
        deps_dir = os.path.join(self.build_folder, "_deps")
        if os.path.isdir(deps_dir):
            for name in os.listdir(deps_dir):
                if "eigen" in name.lower():
                    candidate = os.path.join(deps_dir, name)
                    if os.path.isdir(os.path.join(candidate, "Eigen")):
                        return candidate
        return None

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "Spectra")
        self.cpp_info.set_property("cmake_target_name", "Spectra::Spectra")
        self.cpp_info.libs = []
        # 同时暴露 Spectra 和 Eigen 头文件路径
        self.cpp_info.includedirs = ["include", "include/eigen3"]
