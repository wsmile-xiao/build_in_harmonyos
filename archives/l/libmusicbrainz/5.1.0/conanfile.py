#!/usr/bin/env python3
"""Conan recipe for libmusicbrainz 5.1.0 — MusicBrainz Web Service client (CMake).

libmusicbrainz5 is a C/C++ client library for the MusicBrainz Web Service.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class LibmusicbrainzConan(ConanFile):
    name = "libmusicbrainz"
    version = "5.1.0"
    description = "MusicBrainz Web Service client library (libmusicbrainz5)"
    license = "LGPL-2.1"
    homepage = "https://musicbrainz.org/doc/libmusicbrainz"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        self.requires("neon/0.34.0")
        self.requires("libxml2/2.15.3.1")

    def layout(self):
        cmake_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "OFF" if not self.options.shared else "ON"
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # 上游 cmake/modules/FindLibXml2.cmake / FindNeon.cmake 用 FIND_LIBRARY/
        # FIND_PATH 只搜系统路径，找不到 conan 依赖库（make-c-interface 链接
        # 报 xmlParseFile symbol not found）——显式注入依赖 include/lib 路径。
        xml = self.dependencies["libxml2"].package_folder
        neon = self.dependencies["neon"].package_folder
        # libxml2 include 布局为 include/libxml2/（tree.h 在 include/libxml2/libxml/）
        tc.variables["CMAKE_INCLUDE_PATH"] = os.path.join(xml, "include", "libxml2") + \
            ";" + os.path.join(neon, "include")
        tc.variables["CMAKE_LIBRARY_PATH"] = os.path.join(xml, "lib") + \
            ";" + os.path.join(neon, "lib")
        tc.generate()

    def build(self):
        # make-c-interface 是构建期工具，运行时需加载 libxml2 共享库
        # （libxml2/2.15.3.1 shared=True）——注入 LD_LIBRARY_PATH。
        env = Environment()
        for dep in ("libxml2", "neon"):
            libdir = os.path.join(self.dependencies[dep].package_folder, "lib")
            env.prepend_path("LD_LIBRARY_PATH", libdir)
        cmake = CMake(self)
        with env.vars(self).apply():
            cmake.configure(variables={"CMAKE_POLICY_VERSION_MINIMUM": "3.5"})
            cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "COPYING.txt", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["musicbrainz5"]
        self.cpp_info.set_property("pkg_config_name", "libmusicbrainz5")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]
