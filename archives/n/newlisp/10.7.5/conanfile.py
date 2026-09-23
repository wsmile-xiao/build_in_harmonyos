#!/usr/bin/env python3
"""Conan recipe — newlisp 10.7.5 (configure-alt + make, 纯 C 编程语言解释器)

鸿蒙适配要点：
- configure-alt 未识别 HarmonyOS uname → patches/0001 增加 HarmonyOS→LINUX 映射
- 设备 exec 沙箱只接受静态链接且未 strip 的 ELF → --enable-static + STRIP= true（patches/0002 修复 pipe fdopen 真实 bug）
- 关闭 readline/ffi（无第三方运行时依赖）
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class NewlispConan(ConanFile):
    name = "newlisp"
    version = "10.7.5"
    description = "newLISP is a Lisp-like, general-purpose scripting language. Pure C single interpreted binary."
    license = "GPL-3.0-or-later"
    homepage = "http://www.newlisp.org"
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        # conandata.yml 中 mirror_urls 为文档性镜像列表（字节一致已双源核对），
        # 仅 url/sha256 传给 get()（当前 Conan 2.29 的 get 不支持 mirrors 参数）
        sources = self.conan_data["sources"]
        get(self, url=sources["url"], sha256=sources["sha256"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # R33: 编译器从 Conan conf 获取，禁止依赖 shell 未定义环境变量
        cc = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict).get(
            "c", "clang")
        cflags = "-Wall -Wno-long-long -Wno-strict-aliasing -O2 -c"
        src = self.source_folder
        # configure-alt：非交互配置，生成 makefile_build / makefile_install / config.h。
        # 关闭 readline 与 ffi（无第三方运行时依赖），必须静态链接（设备沙箱限制）。
        # LDFLAGS 显式 "-lm" 避免默认 -ldl 混入静态链接。
        # 用 bash 执行：/system/bin/sh(mksh) 无法 exec 配置探测编译出的 ELF 探针程序。
        self.run(
            'CC="{cc}" CFLAGS="{cflags}" LDFLAGS="-lm" bash ./configure-alt '
            "--disable-readline --disable-ffi --enable-static".format(
                cc=cc, cflags=cflags), cwd=src, env="conanbuild")
        # R9: -j1 而非 -j$(nproc)
        # STRIP=true：设备 exec 沙箱拒绝被 strip 过的 ELF（llvm-strip 后 Permission denied）
        self.run(
            'make -f makefile_build -j1 CC="{cc}" CFLAGS="{cflags}" '
            'LDFLAGS="-static -lm" STRIP=true'.format(cc=cc, cflags=cflags),
            cwd=src, env="conanbuild")

    def package(self):
        # 可执行文件（静态单二进制）+ C 头文件（newlisp.h，供嵌入 API 参考）
        copy(self, "newlisp", src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        copy(self, "newlisp.h", src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"), keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_file_name", "newlisp")
        self.cpp_info.set_property("cmake_target_name", "newlisp::newlisp")