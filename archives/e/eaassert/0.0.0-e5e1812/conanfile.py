#!/usr/bin/env python3
"""Conan recipe — eaassert 0.0.0-e5e1812 (Electronic Arts EAAssert).

EAAssert is EA's simple lightweight assert technology: a small C/C++ library
(source/eaassert.cpp + include/EAAssert/eaassert.h). Upstream builds with CMake
(add_library(EAAssert ...)) and depends on EABase headers (eabase/0699a15,
already published to the ohpcd registry). The upstream CMakeLists.txt has no
install() rules, so package() mirrors the upstream export layout manually:
include/EAAssert/ headers + the built static/shared library.

OHOS adaptation notes:
  - aarch64-linux-ohos: EABase dependency provides EA_PLATFORM detection and
    the header-only base types; no EAAssert source change was required.
  - No CLI produced (library only), so no commands.json is declared (R38).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class EaassertConan(ConanFile):
    name = "eaassert"
    version = "0.0.0-e5e1812"
    description = "EAAssert - Electronic Arts simple and lightweight assert technology"
    license = "BSD-3-Clause"
    homepage = "https://github.com/electronicarts/EAAssert"
    url = "https://github.com/electronicarts/EAAssert"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    generators = "CMakeDeps"

    requires = "eabase/0699a15"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # Upstream declares cmake_minimum_required(VERSION 3.1); modern CMake
        # (>= 3.5) refuses to configure it without this policy minimum.
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.variables["EAASSERT_BUILD_TESTS"] = "OFF"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        # Upstream CMakeLists.txt has no install() rules: mirror the export
        # layout manually (headers + built library). EAAssert is a small
        # assert library: build static lib by default; copy the matching
        # artifact for the requested shared/static option.
        copy(self, "eaassert.h", src=os.path.join(self.source_folder, "include", "EAAssert"),
             dst=os.path.join(self.package_folder, "include", "EAAssert"))
        copy(self, "version.h", src=os.path.join(self.source_folder, "include", "EAAssert"),
             dst=os.path.join(self.package_folder, "include", "EAAssert"))
        if self.options.shared:
            copy(self, "libEAAssert.so*", src=self.build_folder,
                 dst=os.path.join(self.package_folder, "lib"), keep_path=False)
        else:
            copy(self, "libEAAssert.a", src=self.build_folder,
                 dst=os.path.join(self.package_folder, "lib"), keep_path=False)
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        # eaassert.h 公开头文件内 #include "EABase/eabase.h"：公共头文件依赖
        # eabase，必须声明 cpp_info.requires 使消费者获得 eabase 的 include 路径。
        self.cpp_info.requires = ["eabase::eabase"]
        # 兜底：显式把 eabase 包的 include 目录追加进本包 include 路径，
        # 确保消费者即使只链接 eaassert::eaassert 也能解析 <EABase/eabase.h>。
        if "eabase" in self.dependencies:
            ebase_includes = self.dependencies["eabase"].cpp_info.includedirs
            pkg_folder = self.dependencies["eabase"].package_folder
            for rel in ebase_includes:
                abs_dir = os.path.join(pkg_folder, rel) if pkg_folder else rel
                if abs_dir not in self.cpp_info.includedirs:
                    self.cpp_info.includedirs.append(abs_dir)
        self.cpp_info.libs = ["EAAssert"]