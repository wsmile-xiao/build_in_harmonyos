#!/usr/bin/env python3
"""Conan recipe — xmill 0.8 (XMill, a compressor for XML data) for HarmonyOS (arm64).

上游：AT&T Labs Research 的 XMill（XML 压缩器，作者 Hartmut Liefke / Dan Suciu）。
本配方使用镜像 github.com/jungsagacity/xmill 的 master 快照（tarball sha256 固定，
见 conandata.yml）。该快照源码自述版本为 "XMill 0.7 (30 Nov 99)"；请求版本号
0.8 无任何上游证据（AT&T 官方发布站点已下线），差异与取证过程见 notes.md。

产物是 **两个命令行可执行文件**（上游 Options.cpp:PrintUsage() 记录的官方接口）：

* ``bin/xmill``   —— 压缩器（``xmill   [-i file] [-v] [-p path] [-m num] [-1..9] ... file ...``）
* ``bin/xdemill`` —— 解压器（``xdemill [-i file] [-v] [-c] [-d] [-r] [-os num] ... file ...``）

R38：包内含可执行文件 → ``package_type = "application"``，并在软件级目录声明
``archives/x/xmill/commands.json``。

第三方依赖：唯一强制依赖是 **zlib**。上游把 zlib 1.1.3 复制在 ``xmill/zlib/`` 内，
通过 ``#include "../zlib/zlib.h"`` 使用（Windows 风格 ``"..\\zlib\\zlib.h"``）；
适配改为消费制品仓的 ``zlib/1.3.2``（补丁 0002/0008 改写 include），不再编译 vendored
副本。zlib/1.3.2 为静态、-fPIC 构建，链入后可执行文件不引入 ``libz.so`` 运行期依赖，
不污染系统 ``/lib``、``/lib64``（R26）。W0 可消费性证据见 notes.md。

上游构建系统只有 MSVC 工程（xmill.sln + xmill/xmill.vcproj），没有任何
Makefile/CMake/configure；补丁 0001 新增 ``CMakeLists.txt`` 提供 cmake 构建面。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class XmillConan(ConanFile):
    name = "xmill"
    version = "0.8"
    description = ("XMill - a compressor for XML data (structure-aware XML/DTD "
                   "compressor; xmill + xdemill command line tools)")
    license = "AT&T proprietary (non-commercial research use only)"
    homepage = "https://github.com/jungsagacity/xmill"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # 唯一强制第三方依赖（W0: conan download 配方 rc=0 / 二进制 rc=0，见 notes.md）
        self.requires("zlib/1.3.2")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # CMakeDeps 必须生成：否则 find_package(ZLIB) 会落到宿主上其它 zlib
        # （本机实测命中 /storage/Users/currentUser/.harmonybrew 的 ZLIBConfig.cmake），
        # 结果链进动态 libz.so.1 并引入运行期依赖 —— test_package 的鸿蒙用例会拦下。
        deps = CMakeDeps(self)
        deps.generate()
        tc = CMakeToolchain(self)
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
        # 纯命令行工具：只提供可执行文件，不提供库/头文件（R38 → commands.json）
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
