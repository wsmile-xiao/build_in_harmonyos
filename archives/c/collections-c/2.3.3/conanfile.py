#!/usr/bin/env python3
"""Conan recipe for collections-c 2.3.3 — CMake library (static default).

Upstream srdja/Collections-C builds with CMake (project collectc) and installs
libcollectc plus headers under include/collectc/. The tree has no forced
third-party dependencies (pure C, only libc/libm).
"""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get, apply_conandata_patches, export_conandata_patches
import os


class CollectionsCConan(ConanFile):
    name = "collections-c"
    version = "2.3.3"
    description = "A library of generic data structures for the C language"
    license = "LGPL-3.0"
    homepage = "https://github.com/srdja/Collections-C"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    exports_sources = "patches/**"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.variables["CMAKE_INSTALL_SYSTEM_RUNTIME_LIBS_SKIP"] = True
        # Upstream selects static/shared via the SHARED cache variable
        # (default unset => static build).
        tc.variables["SHARED"] = bool(self.options.shared)
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        # 上游静态分支（if(SHARED) 的 else）未设置 PUBLIC_HEADER 属性，
        # cmake.install() 不会安装头文件，导致 include/collectc 缺失；
        # 显式拷贝 src/include/** -> include/collectc/，与 SHARED 分支行为对齐。
        copy(self, "*.h",
             src=os.path.join(self.source_folder, "src", "include"),
             dst=os.path.join(self.package_folder, "include", "collectc"))
        copy(self, "memory/*.h",
             src=os.path.join(self.source_folder, "src", "include"),
             dst=os.path.join(self.package_folder, "include", "collectc", "memory"))
        copy(self, "sized/*.h",
             src=os.path.join(self.source_folder, "src", "include"),
             dst=os.path.join(self.package_folder, "include", "collectc", "sized"))

    def package_info(self):
        self.cpp_info.libs = ["collectc"]
        # Headers install to include/collectc/ (PUBLIC_HEADER DESTINATION
        # include/collectc); expose that directory so plain
        # #include "cc_array.h" works like upstream's own tests.
        self.cpp_info.includedirs = ["include/collectc"]
        self.cpp_info.set_property("cmake_file_name", "collections-c")
        self.cpp_info.set_property("cmake_target_name", "collections-c::collectc")
        self.cpp_info.set_property("pkg_config_name", "collectionc")
