#!/usr/bin/env python3
"""Conan recipe — butteraugli 0-20190319 (psychovisual image similarity metric).

Upstream: https://github.com/google/butteraugli (commit 71b18b636b9c, 2019-03-19)
Build: 上游提供 butteraugli/ 子目录内的 Makefile（无 configure/install 目标）。
  make 编译 butteraugli.o + butteraugli_main.o 并链接出 butteraugli 可执行程序，
  LDLIBS = -lpng -ljpeg。库代码为 butteraugli.o（butteraugli.h API），
  可执行程序即命令行比较工具。本配方：
    - 编译出 butteraugli.o 并用 llvm-ar 归档为 libbutteraugli.a（静态库）
    - 链接 butteraugli 可执行程序到 bin/
    - 安装 butteraugli/butteraugli.h 头文件（保留 #include "butteraugli/butteraugli.h" 用法）
  R33: 编译器/归档器取自 Conan conf，不读裸 shell 环境变量。
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class ButteraugliConan(ConanFile):
    name = "butteraugli"
    version = "0-20190319"
    description = "A tool for measuring perceived differences between images"
    license = "Apache-2.0"
    homepage = "https://github.com/google/butteraugli"
    url = "https://github.com/google/butteraugli"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    # conan 2.29 要求 library 类型声明 shared 选项；上游 Makefile 仅产出
    # 静态库对象，故 shared=True 在 validate() 显式拒绝（避免声实不符）。
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def validate(self):
        if self.options.shared:
            raise ConanInvalidConfiguration(
                "butteraugli 上游 Makefile 仅构建静态库，不支持 shared"
            )

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Makefile 链接 -lpng -ljpeg；zlib 由 libpng 传递引入
        self.requires("libpng/1.6.58")
        self.requires("libjpeg/10")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R33: 编译器/归档器必须来自 Conan conf，绝不裸用 ${CC}/${CXX}
        # 注意：本环境 conan 2.29.1 的 Conf._check_conf_name 不认
        # "tools.build:compiler_executables:cpp" 子键形式，必须整字典读取。
        toolchain = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cxx = toolchain.get("cpp") or "clang++"
        ar = toolchain.get("ar") or "llvm-ar"
        ranlib = toolchain.get("ranlib") or "llvm-ranlib"

        libpng = self.dependencies["libpng"]
        libjpeg = self.dependencies["libjpeg"]

        png_inc = os.path.join(libpng.package_folder, "include")
        png_inc16 = os.path.join(png_inc, "libpng16")
        jpeg_inc = os.path.join(libjpeg.package_folder, "include")
        png_lib = os.path.join(libpng.package_folder, "lib")
        jpeg_lib = os.path.join(libjpeg.package_folder, "lib")

        # 注意：butteraugli.cc 使用 #include "butteraugli/butteraugli.h"，
        # 必须在源码根目录（butteraugli/ 同级）编译，-I.. 由 Makefile 提供。
        cxxflags = (
            "-std=c++11 -I.. "
            f"-I{png_inc} -I{png_inc16} -I{jpeg_inc}"
        )
        ldflags = f"-L{png_lib} -L{jpeg_lib}"

        src_dir = os.path.join(self.source_folder, "butteraugli")
        # R9: 一律 -j1
        self.run(
            f"make -C {src_dir} CXX={cxx} CXXFLAGS='{cxxflags}' "
            f"LDFLAGS='{ldflags}' -j1",
            cwd=self.source_folder,
        )
        # 归档库对象为 libbutteraugli.a（上游无库归档目标，属本配方补充）
        self.run(
            f"cd {src_dir} && {ar} rcs libbutteraugli.a butteraugli.o && {ranlib} libbutteraugli.a",
            cwd=self.source_folder,
        )

    def package(self):
        src_dir = os.path.join(self.source_folder, "butteraugli")
        copy(self, "butteraugli.h", src_dir,
             os.path.join(self.package_folder, "include", "butteraugli"))
        copy(self, "*.a", src_dir, os.path.join(self.package_folder, "lib"))
        copy(self, "butteraugli", src_dir, os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.libs = ["butteraugli"]
        self.cpp_info.bindirs = ["bin"]