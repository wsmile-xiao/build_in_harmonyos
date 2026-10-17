#!/usr/bin/env python3
"""Conan recipe — sjaakii 1.4.1 (CMake, OHOS/aarch64).

Sjaak II — xboard 兼容的国际象棋/变体引擎（Evert Glebbeek, GPL-3.0）。

OHOS 适配要点（详见 notes.md / 补丁）：
  - 任务卡明令 `-DWANT_SSE42=OFF`：上游默认 on 会向 aarch64 注入 -msse4.2
  - CMake 4.x 拒绝 cmake_minimum_required(2.8.12) → CMAKE_POLICY_VERSION_MINIMUM=3.5
    （DRAFT-E321：必须 cache_variables，tc.variables 写进 toolchain 文件不生效）
  - 静态 libreadline.a 需并链 ncursesw（terminfo 后端），补丁内 find_library 处理
  - find_library(M_LIB m) 在 musl/OHOS 必落空 → 补丁置空守卫（止损#8 族）
  - CFLAGS/CXXFLAGS 钉 -O3 -pipe -DNDEBUG（止损#4：挡环境 CFLAGS 泄漏进 configure）
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class SjaakiiConan(ConanFile):
    name = "sjaakii"
    version = "1.4.1"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"
    license = "GPL-3.0-or-later"
    homepage = "http://www.eglebbk.dds.nl/program/chess-index.html"
    url = ""  # CI fills this
    description = "Sjaak II - xboard compatible chess and chess-variant engine"
    topics = ["chess", "xboard", "uci", "perft"]

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("readline/8.3")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # DRAFT-E321/E103: CMake 4.x 拒绝 <3.5 的 cmake_minimum_required；
        # 必须走 cache_variables（-D 命令行），tc.variables 写入 toolchain 文件太晚。
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # 任务卡明令：aarch64 无 SSE，上游 option 默认 on 会注入 -msse4.2 → 关闭
        tc.cache_variables["WANT_SSE42"] = False
        # 止损#4：钉死基础 CFLAGS/CXXFLAGS，挡设备/CI 环境 CFLAGS 泄漏进 configure。
        # 上游 WANT_OPT 仍会追加 -O3 -finline，叠加无害。
        tc.cache_variables["CMAKE_C_FLAGS"] = "-O3 -pipe -DNDEBUG"
        tc.cache_variables["CMAKE_CXX_FLAGS"] = "-O3 -pipe -DNDEBUG"
        # 上游把 DATADIR 烘进二进制（= configure 期 CMAKE_INSTALL_PREFIX）；
        # 指向 conan 包目录使已安装 variants.txt 在运行期可达（consumer 安装时为 None 则保持默认）。
        pkg = self.package_folder
        if pkg:
            tc.cache_variables["CMAKE_INSTALL_PREFIX"] = pkg
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
        # 纯 CLI 应用：只装了 bin/sjaakii，无 lib/include。
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
