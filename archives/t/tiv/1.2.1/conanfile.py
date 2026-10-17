#!/usr/bin/env python3
"""Conan recipe — tiv 1.2.1 (Terminal Image Viewer, plain Makefile + CImg).

tiv 是一个终端图像查看器：用 24-bit RGB ANSI 转义序列 + Unicode 半块字符
(每字符 4x8 像素) 在现代终端里渲染图片。上游只有一个手写 Makefile 和一个
tiv.cpp，没有 configure 脚本、没有测试套件。

Key points:
  - package_type = "application"（只产出 bin/tiv 可执行文件，无库）
  - 硬依赖 cimg/3.6.6（header-only）：上游 tarball 自带 CImg.h 3.3.1，
    但制品仓已有 cimg/3.6.6，按仓库惯例用制品仓版本，头文件从依赖的
    includedirs 取（不用 glob conan 缓存）
  - build() 直接调 make，CXX 从 Conan conf 取（R33），-j1（R9/E074）
  - 上游 Makefile 的 `tiv.o: CImg.h` 规则要求 CImg.h 与 tiv.cpp 同目录，
    所以先把依赖头文件拷进构建目录再 make
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class TivConan(ConanFile):
    name = "tiv"
    version = "1.2.1"
    description = "Terminal Image Viewer - display images in a modern terminal using 24-bit RGB ANSI colors and Unicode block characters"
    license = "Apache-2.0 OR GPL-3.0-or-later"
    homepage = "https://github.com/stefanhaustein/TerminalImageViewer"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    exports_sources = "conandata.yml", "patches/*"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # R36: 依赖必须先发布到制品仓；裸 name/version，不带 channel（R27）
        self.requires("cimg/3.6.6")

    def layout(self):
        basic_layout(self)

    # R32: OHOS 平台兼容
    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # 上游是手写 Makefile，没有 configure 参数需要生成。
        # 工具链通过 make 命令行的 CXX= 传入（见 build()，R33）。
        pass

    def build(self):
        apply_conandata_patches(self)
        # R33: 编译器从 Conan conf 取，CI worker 上 $CXX 不保证存在
        comp_execs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cxx = comp_execs.get("cpp") or "clang++"
        # 上游 Makefile 在 src/ 子目录里（src/{Makefile,tiv.cpp,CImg.h}），
        # 顶层没有 makefile，所以 cwd 指向 src/。
        src_dir = os.path.join(self.source_folder, "src")
        # 上游 Makefile 的默认规则 `tiv.o: CImg.h` 要求头文件与源码同目录。
        # 用制品仓 cimg/3.6.6 的头文件（不 glob conan 缓存），覆盖 tarball
        # 自带的 CImg.h 3.3.1。
        cimg_inc = self.dependencies["cimg"].cpp_info.includedirs[0]
        copy(self, "CImg.h", src=cimg_inc, dst=src_dir)
        # 上游 Makefile 用 `CXXFLAGS ?= -O2 -fpermissive`，-fpermissive 是
        # GCC 专有选项，clang 不认；显式传 CXXFLAGS 覆盖它。
        # Makefile 里 `override CXXFLAGS += -std=c++2a -Wall -fexceptions`，
        # -std 由 Makefile 追加，命令行给的值会被追加在其后。
        # -j1：R9/E074，裸 make 项目不并发。
        self.run(f'make -j1 CXX="{cxx}" CXXFLAGS="-O2"', cwd=src_dir)

    def package(self):
        # 命令行工具：可执行文件进 bin/
        copy(self, "tiv", src=os.path.join(self.source_folder, "src"),
             dst=os.path.join(self.package_folder, "bin"))

    def package_info(self):
        # application 包：没有可链接的库，只有 bindir
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]