#!/usr/bin/env python3
"""Conan recipe for gettext-tiny 0.3.3 — 轻量 gettext 工具集 + libintl（纯 Makefile 构建，无 configure）。

gettext-tiny 是 sabotage-linux 出品的极简 gettext 替代：提供 msgfmt/msgmerge/xgettext/
autopoint 四个 CLI 工具与静态 libintl.a（gettext/dgettext/textdomain 等公开 API）。

关键适配点：
- 纯 Makefile 项目（无 configure 脚本），不能使用 Autotools 工具链；直接 make。
- R26：仅构建静态 libintl.a（默认 LIBINTL 分支，非 MUSL/NONE）。
- 库产物 libintl.a → cpp_info.libs = ["intl"]；头文件 libintl.h；CLI 工具入 bin。
- 无外部依赖；iconv 探测由 Makefile 运行时完成（LDLIBS 探测）。
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class GettexttinyConan(ConanFile):
    name = "gettext-tiny"
    version = "0.3.3"
    description = "轻量 gettext 工具集（msgfmt/msgmerge/xgettext/autopoint）+ 静态 libintl"
    license = "MIT"
    homepage = "https://github.com/sabotage-linux/gettext-tiny"
    url = "https://github.com/sabotage-linux/gettext-tiny"

    # 主交付物是静态 libintl.a + libintl.h（消费者编译链接用），同时安装 CLI 工具；
    # package_type=library 使 CMakeDeps 正常产出 INCLUDE_DIRS/LIBS（application 类型会被丢弃，
    # 导致 test_package/消费者无法找到 libintl.h，误用工具链 stub 后报 undeclared gettext）
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # 纯 Makefile 项目：直接在源码目录 make（Makefile 产物就地生成）
        self.run("make -j1 CC=clang AR=llvm-ar RANLIB=llvm-ranlib",
                 cwd=self.source_folder)

    def package(self):
        src = self.source_folder
        # 库 + 头文件 + CLI 工具 + m4/data 数据（均在 source_folder 内生成）
        copy(self, "*.h", os.path.join(src, "include"),
             os.path.join(self.package_folder, "include"))
        copy(self, "*.a", src, os.path.join(self.package_folder, "lib"))
        for tool in ("msgfmt", "msgmerge", "xgettext", "autopoint"):
            copy(self, tool, src, os.path.join(self.package_folder, "bin"))
        copy(self, "*.m4", os.path.join(src, "m4"),
             os.path.join(self.package_folder, "share", "gettext-tiny", "m4"))
        copy(self, "*", os.path.join(src, "data"),
             os.path.join(self.package_folder, "share", "gettext-tiny", "data"))

    def package_info(self):
        # application 类型默认不传播 include 目录，需显式声明（否则消费者误用工具链 stub libintl.h）
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libs = ["intl"]
        self.cpp_info.bindirs = ["bin"]