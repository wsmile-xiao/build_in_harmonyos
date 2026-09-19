#!/usr/bin/env python3
"""Conan recipe for libmusicbrainz5 5.1.0-git20150707 — MusicBrainz Web Service client (CMake).

libmusicbrainz5 是 MusicBrainz Web Service 的 C/C++ 客户端库。
版本 5.1.0-git20150707 对应 Debian 源包 libmusicbrainz5 的 5.1.0+git20150707-N
（上游 5.1.0 之后未再发布 release，各发行版改用 git 快照）；源码取上游
metabrainz/libmusicbrainz 在 2015-07-07 当日 master HEAD
（commit 97f98a6e04d6ae0bc7c1a7f8003e25b6c364d59b）。

相比 release-5.1.0（2014-11-13），该快照把 C 接口拆分为独立库
musicbrainz5cc，并新增 libmusicbrainz5cc.pc。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy


class Libmusicbrainz5Conan(ConanFile):
    name = "libmusicbrainz5"
    version = "5.1.0-git20150707"
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
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # 上游 cmake_minimum_required(VERSION 2.6) 在 CMake 4.x 下被移除兼容模式，
        # 需显式回退（知识条目 E103）。注意：CMAKE_POLICY_VERSION_MINIMUM 必须在
        # 解析 CMakeLists 第 1 行之前即生效，故通过 -D 命令行参数传入（写在
        # toolchain 里太晚，cmake_minimum_required 已经报错）。
        # 上游 cmake/modules/FindLibXml2.cmake / FindNeon.cmake 仅用
        # FIND_PATH/FIND_LIBRARY 搜索系统路径，无法发现 Conan 依赖；显式注入
        # 依赖的 include/lib 搜索路径（知识条目 E216）。
        xml = self.dependencies["libxml2"].package_folder
        neon = self.dependencies["neon"].package_folder
        tc.variables["CMAKE_INCLUDE_PATH"] = os.path.join(xml, "include", "libxml2") + \
            ";" + os.path.join(neon, "include")
        tc.variables["CMAKE_LIBRARY_PATH"] = os.path.join(xml, "lib") + \
            ";" + os.path.join(neon, "lib")
        tc.generate()

    def build(self):
        # make-c-interface 是构建期可执行工具，运行时需加载 libxml2 共享库。
        # 注意顺序：OHOS SDK 的 lld（links 阶段调用）自身依赖 SDK llvm/lib 下的
        # libxml2.so.16，若把 Conan libxml2 的 lib 目录前置到 LD_LIBRARY_PATH，
        # lld 会加载到 ABI 不兼容的同名库，报 "Error loading shared library
        # libxml2.so.16" / "xmlFreeDoc: symbol not found"。因此 SDK 路径在前，
        # Conan 依赖路径追加在后（知识条目 E120/E132/E266）。
        env = Environment()
        sdk_llvm_lib = "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib"
        if os.path.isdir(sdk_llvm_lib):
            env.prepend_path("LD_LIBRARY_PATH", sdk_llvm_lib)
        for dep in ("libxml2", "neon"):
            libdir = os.path.join(self.dependencies[dep].package_folder, "lib")
            env.append_path("LD_LIBRARY_PATH", libdir)
        cmake = CMake(self)
        with env.vars(self).apply():
            cmake.configure(cli_args=["-DCMAKE_POLICY_VERSION_MINIMUM=3.5"])
            cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "COPYING.txt", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.set_property("pkg_config_name", "libmusicbrainz5")
        self.cpp_info.libs = ["musicbrainz5", "musicbrainz5cc"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]
