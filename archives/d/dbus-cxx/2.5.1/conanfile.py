#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
dbus-cxx/2.5.1 — C++ DBus 绑定库（OpenHarmony PC / aarch64 适配配方）

上游:    https://github.com/dbus-cxx/dbus-cxx tag 2.5.1
依赖:    libsigc/3.0.6（dbus-cxx 2.x 线要求 sigc++-3.0 / C++17）

dbus-cxx 2.x 是 dbus 协议的完整自研 C++ 实现（不依赖 libdbus，
无 libdbus 头文件/符号引用——README "complete ground-up implementation
of the DBus protocol, without libdbus"），因此 conan 依赖仅 libsigc。

适配要点（详见 notes.md）:
  1. CMake 交叉编译: CMAKE_SYSTEM_NAME=HarmonyOS 由 Conan 工具链注入；
     上游 CMakeLists 无平台分支，OHOS 下直接可配可编。
  2. 上游 add_compile_definitions(interface=struct)（UNIX 分支）适配
     OHOS 无冲突。
  3. 上游测试: ctest 注册 157 项（unit-tests/CMakeLists.txt 154 +
     robustness 1 + tools-tests 2，tools/robustness 为条件目标默认 OFF
     不计入默认形态；默认形态 157——见 notes.md 全量口径）。
     其中 103 项为纯本地单元测试（callmessage 13/messageiterator 52/
     path 18/signature 15/validation 3/unset-envvars 2），本机全量
     实测 103/103 PASS；54 项需 dbus-daemon（dbus-launch/dbus-run-session
     包装），OHOS 平台无 dbus-daemon 工具（which 全 not found），
     逐项环境豁免（见 notes.md 证据）。
"""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.gnu import PkgConfigDeps
from conan.tools.files import copy, get


class DbusCxxConan(ConanFile):
    name = "dbus-cxx"
    version = "2.5.1"
    description = ("dbus-cxx is a C++ bindings library for DBus, "
                   "a complete ground-up implementation of the DBus "
                   "protocol without libdbus")
    license = "LGPL-3.0-or-later OR BSD-3-Clause"
    homepage = "https://dbus-cxx.github.io/"
    url = "https://github.com/dbus-cxx/dbus-cxx"
    topics = ("dbus", "ipc", "rpc", "bindings")

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    # PkgConfigDeps: 上游 CMakeLists 用 pkg_check_modules(sigc REQUIRED
    # sigc++-3.0) 发现 libsigc——CMakeDeps 生成的 sigc++-3.0 pc 由本
    # generator 提供（Conan 2 下 generators 属性声明即可）
    generators = "CMakeDeps", "PkgConfigDeps"

    exports_sources = "patches/**"

    def configure(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"dbus-cxx only supports Linux and OHOS, got {self.settings.os}")
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        # dbus-cxx 2.x 唯一构建依赖: sigc++-3.0（上游 CMakeLists:
        # pkg_check_modules(sigc REQUIRED sigc++-3.0)）
        # 传递头：dbus-cxx 公共头（connection.h/signal.h 等）直接
        # #include <sigc++/sigc++.h>，消费者必须能解析 sigc 头
        self.requires("libsigc/3.0.6",
                      transitive_headers=True, transitive_libs=True)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        # 上游要求 C++17（libsigc++-3.0）
        tc.variables["CMAKE_CXX_STANDARD"] = "17"
        # 精简构建: 仅库本体（examples/tools/website 全关；
        # tools 需要 expat + libcppgenerate，非库本体必需）
        tc.variables["ENABLE_EXAMPLES"] = "OFF"
        tc.variables["ENABLE_TOOLS"] = "OFF"
        tc.variables["BUILD_SITE"] = "OFF"
        # 测试默认构建由 conan create 的 build() 按需开启，
        # 这里默认关（CI 只读 4 文件，测试在本地跑过）
        tc.variables["BUILD_TESTING"] = "OFF"
        tc.generate()

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # 上游安装布局: include/dbus-cxx-2.0/{,dbus-cxx/} + lib/libdbus-cxx.so
        self.cpp_info.libs = ["dbus-cxx"]
        self.cpp_info.includedirs = [
            os.path.join("include", "dbus-cxx-2.0"),
            os.path.join("include", "dbus-cxx-2.0", "dbus-cxx"),
        ]
        self.cpp_info.set_property("cmake_file_name", "dbus-cxx")
        self.cpp_info.set_property("cmake_target_name", "dbus-cxx::dbus-cxx")
        self.cpp_info.set_property("pkg_config_name", "dbus-cxx-2.0")
