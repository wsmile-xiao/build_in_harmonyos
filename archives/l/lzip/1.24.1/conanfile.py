#!/usr/bin/env python3
"""Conan recipe — lzip 1.24.1 (LZMA lossless compressor, 自研 configure).

lzip 是 LZMA 无损压缩器（Antonio Diaz Diaz），上游用自研 configure 脚本
（非 autoconf）+ 纯 C++（无外部库依赖），产物为可执行文件 lzip。

OHOS 适配要点（详见 notes.md）：
- 零外部依赖（R33）：产物为单个可执行文件，无第三方库链接。
- 自研 configure（非 autoconf）**只接受命令行 `var=value` 赋值，忽略环境变量**；默认
  `CXX=g++`，`${CXX} --version` 探测失败时回退 `c++`（设备不存在）并把 CXXFLAGS 重置为
  `-O2` ⇒ CXX 必须作为 configure **参数**显式传入（取自 profile compiler_executables）。
  交叉安全：configure 不运行构建产物。
- 上游测试 testsuite/check.sh 为单 runner 脚本（N_static=220 个断言块，
  经验汇总 §12.72 RUNTEST 脚本口径），在 build() 内 make check 真实执行。
- -j1：GNU make jobserver 在 HMDFS 上创建 command FIFO 失败（既有先例）。
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.layout import basic_layout


class LzipConan(ConanFile):
    name = "lzip"
    version = "1.24.1"
    description = "lzip — LZMA lossless data compressor"
    license = "GPL-2.0-or-later"
    homepage = "https://www.nongnu.org/lzip/lzip.html"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    exports_sources = "patches/*"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True,
            retry=5, retry_wait=10)

    def generate(self):
        VirtualBuildEnv(self).generate()

    def build(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"lzip does not support os={self.settings.os}"
            )
        apply_conandata_patches(self)
        # 自研 configure：CXXFLAGS/LDFLAGS 来自 conanbuild 环境（profile
        # [buildenv]，R33）；CXX 必须显式传入——buildenv 不导出 CXX，configure
        # 的 g++ 探测失败会回退到不存在的 c++ 并重置 CXXFLAGS。
        comp = self.conf.get("tools.build:compiler_executables") or {}
        cxx = comp.get("cpp", "clang++")
        self.run(
            f"cd {self.source_folder} && ./configure --prefix={self.package_folder}/usr CXX={cxx}",
            env="conanbuild",
        )
        # -j1：HMDFS jobserver FIFO 先例
        self.run(f"cd {self.source_folder} && make -j1", env="conanbuild")
        # 上游测试（R51 口径）：testsuite/check.sh 单 runner、220 断言块，
        # 全部针对构建出的 lzip 二进制真实执行。
        self.run(f"cd {self.source_folder} && make check -j1", env="conanbuild")

    def package(self):
        # 只装二进制（install-bin），避开 install-info 对宿主工具的依赖；
        # 上游自研 configure 硬编码 INSTALL_*=/usr/bin/install*，HMDFS 用户态
        # 无 install 命令（Error 127 实证）——用 make 命令行变量覆盖为
        # cp/mkdir 等价语义，CI worker 上同样可用。
        self.run(
            f"cd {self.source_folder} && make install-bin "
            'INSTALL="cp -f" INSTALL_PROGRAM="cp -f" INSTALL_DATA="cp -f" '
            'INSTALL_DIR="mkdir -p"',
            env="conanbuild",
        )

    def package_info(self):
        self.cpp_info.bindirs = ["usr/bin"]
