#!/usr/bin/env python3
"""Conan recipe for DEXTRACTOR 1.0 — compression/decompression command library.

DEXTRACTOR (Gene Myers) 提供 5 个命令行工具:
  - dextract : 从 PacBio .bax.h5 (HDF5) 提取 subread / QV 数据（唯一依赖 HDF5 的工具）
  - dexta/undexta : .fasta 与 2-bit .dexta 压缩格式互转
  - dexqv/undexqv : .quiva 与 Huffman 压缩 .dexqv 格式互转

构建系统: 上游 Makefile（经 0001 补丁可移植化: gcc → $(CC), PATH_HDF5/DEST_DIR 可覆盖）。
依赖: hdf5/1.14.6（制品仓已发布；libaec/1.1.7、zlib/1.3.1.1 为其传递依赖）。
"""
import os

from conan import ConanFile
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get)
from conan.tools.layout import basic_layout


class DextractorConan(ConanFile):
    name = "dextractor"
    version = "1.0"
    description = "Decompression and compression commands for PacBio .bax.h5, .fasta and .quiva files"
    license = "BSD-3-Clause"
    homepage = "https://github.com/thegenemyers/DEXTRACTOR"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def configure(self):
        self.settings.rm_safe("os.version")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def requirements(self):
        # 制品仓已发布（PF4 依赖闸探测通过）: hdf5/1.14.6
        self.requires("hdf5/1.14.6")

    def build(self):
        apply_conandata_patches(self)
        # R33: 编译器取自 Conan conf（CI 上 ${CC} 为空），禁止从 shell 环境取
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = compilers.get("c", "clang")
        # 上游 Makefile 以 PATH_HDF5 前缀定位 hdf5 的 include/ 与 lib/，指向 Conan 依赖包目录
        hdf5 = self.dependencies["hdf5"]
        self.run(f'make CC="{cc}" PATH_HDF5="{hdf5.package_folder}" -j1',
                 cwd=self.source_folder)

    def package(self):
        for tool in ("dextract", "dexta", "undexta", "dexqv", "undexqv"):
            copy(self, tool, src=self.source_folder,
                 dst=os.path.join(self.package_folder, "bin"))
        # 上游无独立 LICENSE 文件，许可证文本在每个源文件头部；附带 README 备查
        copy(self, "README", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
