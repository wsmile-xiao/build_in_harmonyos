#!/usr/bin/env python3
"""Conan recipe — ekhtml 0.3.2 (Autotools).

El-Kabong HTML: high-speed forgiving SAX-style HTML parser.
Zero external dependencies (libc only).
"""
from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches
from conan.tools.layout import basic_layout
import os

required_conan_version = ">=2.0"


class EkhtmlConan(ConanFile):
    name = "ekhtml"
    version = "0.3.2"
    package_type = "library"

    description = "High-speed forgiving SAX-style HTML parser (zero deps)"
    homepage = "https://ekhtml.sourceforge.net/"
    license = "BSD-2-Clause"
    url = "https://github.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    exports_sources = "patches/*"

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        top = self.source_folder
        # OHOS 沙箱适配（三处绕过，均经验证）：
        # 1. config.status 临时目录须在可写位置（$HOME 根目录 mktemp 受限）
        os.environ["TMPDIR"] = self.build_folder
        # 2. configure 显式参数（等价 AutotoolsToolchain 默认）
        conf = ("--disable-shared --enable-static --prefix=/ "
                "'--bindir=${prefix}/bin' '--sbindir=${prefix}/bin' "
                "'--libdir=${prefix}/lib' '--includedir=${prefix}/include' "
                "'--oldincludedir=${prefix}/include' --enable-static --disable-shared")
        self.run(f"cd {top} && CC=clang ./configure {conf}")
        # config.status 首次生成 Makefile 可能为空（沙箱竞态），循环重跑
        # 直到每个 Makefile 非空（-s 检查），全量重跑会卡在 .deps 乱码阶段
        for mf in ("Makefile", "src/Makefile", "include/Makefile",
                   "testsuite/Makefile", "docs/Makefile"):
            self.run(f"cd {top} && while [ ! -s {mf} ]; do "
                     f"TMPDIR={self.build_folder} sh ./config.status {mf}; done")
        # 3. config.status 生成的 Makefile 部分变量被污染（top_srcdir 乱码），
        #    make 命令行覆盖 top_srcdir；.deps include 容错（GNU make）
        #    （单引号保护 $(DEPDIR)，避免 shell 展开）；预建 .deps 目录
        #    （clang -MF 写依赖文件需目录存在）
        self.run(f"cd {top} && mkdir -p src/.deps include/.deps testsuite/.deps")
        self.run(f"cd {top} && find . -name Makefile -exec sed -i "
                 "'s|^include ./$(DEPDIR)|-include ./$(DEPDIR)|' {} +")
        self.run(f"cd {top} && make top_srcdir={top} -j1")

    def package(self):
        top = self.source_folder
        # install_sh 变量被污染（5*./install-sh 乱码），make 命令行覆盖后 install；
        # --prefix=/ 需用 DESTDIR 重定向到 package 目录（/lib 根目录只读）
        self.run(f'cd {top} && make install top_srcdir={top} '
                 f'"install_sh=$(SHELL) {top}/install-sh" '
                 f'DESTDIR={self.package_folder}')
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "ekhtml")
        self.cpp_info.set_property("cmake_target_name", "ekhtml::ekhtml")
        self.cpp_info.libs = ["ekhtml"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]