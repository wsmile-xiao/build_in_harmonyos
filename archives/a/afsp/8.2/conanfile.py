#!/usr/bin/env python3
"""Conan recipe for AFsp 8.2 — audio file utility programs and routines.

AFsp 是 McGill 音频文件处理工具集（纯 C，Makefile 构建）：
- libtsp.a + libAO.a（音频文件 I/O 库）
- bin/ 下 10 个工具：InfoAudio/CompAudio/CopyAudio/FiltAudio/GenNoise/
  GenTone/LPanal/LPsyn/PQevalAudio/ResampAudio
无外部 Conan 依赖（仅 -lm）。上游测试：test/ 目录 make test
（txxxAudio | filter_log 对比 txxxAudio.ref 参考输出）。
"""
import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class AfspConan(ConanFile):
    name = "afsp"
    version = "8.2"
    description = "Audio file utility programs and routines (AFsp)"
    license = "Custom"
    homepage = "https://www-mmsp.ece.mcgill.ca/Documents/Downloads/AFsp/"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)
        # AFsp Makefile 用 dist_dir=../.. 相对路径输出 lib/ 与 bin/，
        # 必须 in-source 构建（产物直接落在源码目录）
        self.folders.build = "."

    def source(self):
        # URL 无 .tar.gz 扩展名（服务器文件名即 AFsp-v8r2.tar.gz，但 URL 路径
        # 以 .tar.gz 结尾，conan 可正确识别）；strip_root=True 去掉 AFsp-v8r2/ 前缀
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # R33: Get compiler from Conan conf, not shell env vars
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang") if compilers else "clang"
        # 顶层 make = libtsp + libAO + audio（生成 lib/ 与 bin/），in-source
        self.run(f"make -j1 CC={cc}", cwd=self.source_folder)
        # 上游测试：test/Makefile 运行 txxxAudio | filter_log 对比参考输出
        self.run(f"make -C test CC={cc}", cwd=self.source_folder)

    def package(self):
        # 工具集：拷贝 bin/ 全部可执行 + 库 + 头文件
        copy(self, "*", src=os.path.join(self.build_folder, "bin"),
             dst=os.path.join(self.package_folder, "bin"))
        copy(self, "*.a", src=os.path.join(self.build_folder, "lib"),
             dst=os.path.join(self.package_folder, "lib"))
        copy(self, "*.h", src=os.path.join(self.source_folder, "include"),
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "libtsp", src=os.path.join(self.source_folder, "include"),
             dst=os.path.join(self.package_folder, "include"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libs = ["AO", "tsp"]
