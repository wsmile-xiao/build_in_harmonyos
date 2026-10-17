#!/usr/bin/env python3
"""Conan recipe — convlit 1.8 (ConvertLIT，.LIT 电子书转换工具).

convlit (clit) 将 Microsoft Reader .LIT 文件解包为 OEBPS/HTML。
构建系统：Makefile（lib/ 静态库 + clit18/clit 二进制）
平台：OHOS aarch64 / Linux
依赖：libtommath
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, copy
from conan.tools.layout import basic_layout
from conan.tools.env import Environment


class ConvlitConan(ConanFile):
    name = "convlit"
    version = "1.8"
    description = "convlit — 将 Microsoft Reader .LIT 文件转换为 HTML/OEBPS"
    license = "GPL-2.0-or-later"
    homepage = "https://www.kyzer.me.uk/pack/convlit/"
    url = ""
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"
    # 导出 patches/ 到 conan 缓存（apply_conandata_patches 需在源码目录找到补丁）
    exports_sources = "patches/*"

    def requirements(self):
        self.requires("libtommath/1.3.0")

    def layout(self):
        basic_layout(self)

    def generate(self):
        # OHOS 工具链通过 profile [conf] tools.build:compiler_executables 提供。
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c", "clang")
        tommath = self.dependencies["libtommath"]
        tinc = os.path.join(tommath.package_folder, "include")
        tlib = os.path.join(tommath.package_folder, "lib")
        env = Environment()
        env.define("CC", cc)
        env.define("AR", "llvm-ar")
        env.define("RANLIB", "llvm-ranlib")
        env.append("CFLAGS", "-I%s" % tinc)
        env.append("LDFLAGS", "-L%s" % tlib)
        env.vars(self).save_script("conanbuild_convlit")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=False)
        # 上游为 2004 年 Windows 源码包，orig 内是 CRLF；先统一换行为 LF
        # 保证 patch 可精确应用，同时让 Makefile 在 GNU make 下解析正确。
        for root, _dirs, files in os.walk(self.source_folder):
            for fn in files:
                if fn.endswith((".c", ".h", "Makefile")):
                    p = os.path.join(root, fn)
                    with open(p, "rb") as fh:
                        data = fh.read()
                    if b"\r\n" in data:
                        data = data.replace(b"\r\n", b"\n")
                        with open(p, "wb") as fh:
                            fh.write(data)
        apply_conandata_patches(self)

    def build(self):
        # lib/ 先产出 openclit.a，clit18/ 再链接 clit 可执行文件；
        # 上游 Makefile 硬编码 gcc/ar/本地 libtommath 路径，已由 patch
        # 改为 $(CC)/$(AR)/-ltommath（CFLAGS/LDFLAGS 从 conan 环境注入）。
        self.run("make -C lib -j1", cwd=self.source_folder,
                 env=["conanbuild_convlit"])
        self.run("make -C clit18 -j1", cwd=self.source_folder,
                 env=["conanbuild_convlit"])

    def package(self):
        # 注意：dst 必须为绝对路径（相对路径会被 conan 解析到 build 目录，
        # 导致 package_folder/bin 为空、test_package 运行 clit 时 "not found"）。
        bindir = os.path.join(self.package_folder, "bin")
        os.makedirs(bindir, exist_ok=True)
        copy(self, "clit", src=os.path.join(self.source_folder, "clit18"),
             dst=bindir)

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.bindirs = ["bin"]
