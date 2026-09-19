#!/usr/bin/env python3
"""Conan recipe for list 0.4.1 (clibs/list).

clibs/list 是纯 Makefile 项目（无 configure 脚本）：
  make           → build/libclibs_list.a + build/libclibs_list.so.0.4.1
  make test      → 编译并运行 bin/test（12 个上游断言测试）
  make install DESTDIR=... → 安装 libclibs_list.{a,so*} 与 include/clibs/list.h

R26: 系统同名库默认静态。list 无同名系统库冲突，但按平台惯例默认 static，
shared 选项仍保留（Makefile 原生支持 .so 构建）。
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class ListConan(ConanFile):
    name = "list"
    version = "0.4.1"
    description = "Simple doubly-linked list C library (clibs/list, TJ Holowaychuk)"
    license = "MIT"
    homepage = "https://github.com/clibs/list"
    url = "https://github.com/clibs/list"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

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
        # 纯 Makefile 构建：编译库 + 运行上游测试（CI 与本地 W3 同源）。
        # basic_layout 将 build_folder 置于 build-release/，须在 source_folder
        # 内执行 make（Makefile 在源码根）。
        self.run("make CC=clang AR=llvm-ar RANLIB=llvm-ranlib -j1",
                 cwd=self.source_folder)
        self.run("make bin/test CC=clang AR=llvm-ar RANLIB=llvm-ranlib && ./bin/test",
                 cwd=self.source_folder)

    def package(self):
        # 直接拷贝安装产物到 package_folder（Makefile install 已定义布局）。
        # 注意：copy() 会按 src 目录展开 pattern，须将 src 精确到 build/ 与 src/，
        # 否则会在 package 内残留 build/、src/ 中间层级导致 CMakeDeps 找不到库。
        copy(self, "libclibs_list.a",
             os.path.join(self.source_folder, "build"),
             os.path.join(self.package_folder, "lib"))
        if self.options.shared:
            copy(self, "libclibs_list.so*",
                 os.path.join(self.source_folder, "build"),
                 os.path.join(self.package_folder, "lib"))
        copy(self, "list.h",
             os.path.join(self.source_folder, "src"),
             os.path.join(self.package_folder, "include", "clibs"))

    def package_info(self):
        self.cpp_info.libs = ["clibs_list"]
        self.cpp_info.includedirs = ["include"]
        # 头文件路径为 <clibs/list.h>
        self.cpp_info.bindirs = []