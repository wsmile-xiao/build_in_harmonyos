#!/usr/bin/env python3
"""Conan recipe — sfsexp 1.4.1 (Small, Fast S-Expression Library).

sfsexp 是 C 语言的 S-表达式（S-Expression）解析和操作库，提供 parse_sexp、
print_sexp、destroy_sexp 等 API。无外部依赖，仅依赖 libc。

构建系统：autotools（./configure && make && make install）

4 个平台适配补丁（已在 patches/ 目录）：
  - 0001-Makefile.in.patch: umask 077→007（HMDFS 权限修复）
  - 0002-config.guess.patch: 添加 HarmonyOS 检测块
  - 0003-config.sub.patch: 添加 ohos-linux triplet + linux-ohos* OS 模式
  - 0004-configure.patch: umask 077→007（configure 脚本）
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain


class SfsexpConan(ConanFile):
    name = "sfsexp"
    version = "1.4.1"
    description = "Small, Fast S-Expression Library for C"
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/mjsottile/sfsexp"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "sfsexp")
        self.cpp_info.set_property("cmake_target_name", "sfsexp::sfsexp")
        self.cpp_info.set_property("pkg_config_name", "sfsexp")
        self.cpp_info.libs = ["sexp"]
        self.cpp_info.includedirs = ["include"]
