#!/usr/bin/env python3
# 权限: 本配方在 OHOS PC 平台适配使用
"""
Conan recipe — btree.c 0.6.4 (plain C library, tidwall/btree.c).

B-tree implementation in C (generic, variable-sized items, copy-on-write).
Pure libc (C99 + optional C11 <stdatomic.h> refcount), no external deps.
Upstream ships no Makefile/CMake build system (only tests/run.sh test
harness), so the recipe compiles btree.c directly into a static library
and installs the public btree.h header (R26, same pattern as b64.c).
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, export_conandata_patches, apply_conandata_patches
from conan.tools.layout import basic_layout
from conan.errors import ConanInvalidConfiguration

required_conan_version = ">=2.0"


class BtreeCConan(ConanFile):
    name = "btree.c"
    version = "0.6.4"
    package_type = "library"

    description = "B-tree implementation in C (tidwall/btree.c)"
    homepage = "https://github.com/tidwall/btree.c"
    license = "MIT"
    url = "https://github.com/tidwall/btree.c"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def validate(self):
        # R26: 库仅以静态形式交付（上游无共享库安装规则）
        if self.options.shared:
            raise ConanInvalidConfiguration("btree.c is static-only")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # R33: 编译器取自 Conan 配置（tools.build:compiler_executables），
        # 不依赖未定义的 shell 环境变量。
        cc_conf = self.conf.get("tools.build:compiler_executables", default={})
        cc = (cc_conf or {}).get("c", "clang")
        pic = "-fPIC" if self.options.fPIC else ""
        # C11（<stdatomic.h> 引用计数）；BTREE_NOATOMICS 保留 C99 回退。
        self.run(f"{cc} -std=c11 -Wall -O2 {pic} -c btree.c -o btree.o",
                 cwd=self.source_folder)
        self.run("ar rcs libbtree.a btree.o",
                 cwd=self.source_folder)

    def package(self):
        copy(self, "btree.h", src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "libbtree.a", src=self.source_folder,
             dst=os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.libs = ["btree"]
